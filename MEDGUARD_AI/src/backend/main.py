"""FastAPI service for the local, synthetic-only MedGuard AI demonstration."""

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from typing import Iterator, Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .security_engine import Finding, evaluate_telemetry


load_dotenv()
ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "src" / "frontend"
PUBLIC_DIR = ROOT / "public"
METRIC_UNITS = {
    "heart_rate": "bpm",
    "spo2": "%",
    "temperature_c": "°C",
    "respiratory_rate": "breaths/min",
}


class TelemetryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    device_id: str = Field(
        min_length=2,
        max_length=64,
        pattern=r"^(?:monitor-01|pump-02|gateway-01|unregistered-sim-[0-9]{2})$",
    )
    metric: Literal["heart_rate", "spo2", "temperature_c", "respiratory_rate"]
    value: float = Field(ge=0, le=300, allow_inf_nan=False)
    source_network: Literal["clinical-sim-net", "untrusted-sim-net"] = "clinical-sim-net"
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Acknowledgement(BaseModel):
    alert_id: str
    status: Literal["acknowledged"]
    acknowledged_at: datetime


def _sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("DATABASE_URL must be a local SQLite URL starting with sqlite:///")
    raw_path = database_url[len(prefix) :]
    if not raw_path or raw_path == ":memory:":
        raise ValueError("DATABASE_URL must name a persistent SQLite file")
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


@contextmanager
def _connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _initialize_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id TEXT PRIMARY KEY,
                observed_at TEXT NOT NULL,
                device_id TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                source_network TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL REFERENCES telemetry(id),
                rule_id TEXT NOT NULL,
                title TEXT NOT NULL,
                severity TEXT NOT NULL CHECK (severity IN ('medium', 'high')),
                description TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'acknowledged')),
                created_at TEXT NOT NULL,
                acknowledged_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_telemetry_observed_at
                ON telemetry(observed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_alerts_created_at
                ON alerts(created_at DESC);
            """
        )

        existing = connection.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]
        if existing == 0:
            samples = [
                ("monitor-01", "heart_rate", 72.0, "clinical-sim-net"),
                ("pump-02", "temperature_c", 37.0, "clinical-sim-net"),
                ("gateway-01", "spo2", 97.0, "clinical-sim-net"),
                ("unregistered-sim-01", "spo2", 84.0, "clinical-sim-net"),
            ]
            for device_id, metric, value, network in samples:
                event = {
                    "device_id": device_id,
                    "metric": metric,
                    "value": value,
                    "source_network": network,
                }
                _store_event(connection, event, _utc_now())


def _event_payload(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "observed_at": row["observed_at"],
        "device_id": row["device_id"],
        "metric": row["metric"],
        "value": row["value"],
        "unit": row["unit"],
        "source_network": row["source_network"],
        "synthetic": True,
    }


def _alert_payload(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "event_id": row["event_id"],
        "rule_id": row["rule_id"],
        "title": row["title"],
        "severity": row["severity"],
        "description": row["description"],
        "recommended_action": row["recommended_action"],
        "status": row["status"],
        "created_at": row["created_at"],
        "acknowledged_at": row["acknowledged_at"],
        "synthetic": True,
    }


def _store_event(
    connection: sqlite3.Connection,
    event: dict[str, object],
    observed_at: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    event_id = str(uuid4())
    metric = str(event["metric"])
    connection.execute(
        """
        INSERT INTO telemetry
            (id, observed_at, device_id, metric, value, unit, source_network)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            observed_at,
            str(event["device_id"]),
            metric,
            float(event["value"]),
            METRIC_UNITS[metric],
            str(event["source_network"]),
        ),
    )
    findings = evaluate_telemetry(event)
    alerts: list[dict[str, object]] = []
    for finding in findings:
        alerts.append(_store_alert(connection, event_id, finding))
    row = connection.execute("SELECT * FROM telemetry WHERE id = ?", (event_id,)).fetchone()
    return _event_payload(row), alerts


def _store_alert(
    connection: sqlite3.Connection,
    event_id: str,
    finding: Finding,
) -> dict[str, object]:
    alert_id = str(uuid4())
    created_at = _utc_now()
    connection.execute(
        """
        INSERT INTO alerts
            (id, event_id, rule_id, title, severity, description,
             recommended_action, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)
        """,
        (
            alert_id,
            event_id,
            finding.rule_id,
            finding.title,
            finding.severity,
            finding.description,
            finding.recommended_action,
            created_at,
        ),
    )
    row = connection.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    return _alert_payload(row)


def _create_telemetry(database_path: Path, payload: TelemetryInput) -> dict[str, object]:
    observed_at = payload.observed_at
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    event = payload.model_dump()
    event["observed_at"] = observed_at.astimezone(timezone.utc).isoformat()
    with _connect(database_path) as connection:
        stored_event, alerts = _store_event(
            connection,
            event,
            str(event["observed_at"]),
        )
    return {"event": stored_event, "alerts": alerts}


def create_app(database_url: str | None = None) -> FastAPI:
    selected_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./medguard.db")
    database_path = _sqlite_path(selected_url)
    _initialize_database(database_path)

    application = FastAPI(
        title="MedGuard AI",
        description=(
            "Local synthetic healthcare-IoT telemetry demonstration. "
            "Alerts are advisory and are not clinical assessments."
        ),
        version="1.0.0",
    )
    application.state.database_path = database_path
    application.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")
    application.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

    @application.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")

    @application.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "MedGuard AI",
            "mode": "synthetic-demo",
            "synthetic_data_only": True,
        }

    @application.get("/api/telemetry")
    def list_telemetry(
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, object]:
        with _connect(database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM telemetry ORDER BY observed_at DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return {"items": [_event_payload(row) for row in rows], "synthetic": True}

    @application.get("/api/alerts")
    def list_alerts(
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, object]:
        with _connect(database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM alerts ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return {"items": [_alert_payload(row) for row in rows], "synthetic": True}

    @application.post("/api/telemetry", status_code=201)
    def submit_telemetry(payload: TelemetryInput) -> dict[str, object]:
        return _create_telemetry(database_path, payload)

    @application.post("/api/simulate/anomaly", status_code=201)
    def simulate_anomaly() -> dict[str, object]:
        payload = TelemetryInput(
            device_id="unregistered-sim-02",
            metric="spo2",
            value=84,
            source_network="clinical-sim-net",
        )
        return _create_telemetry(database_path, payload)

    @application.post("/api/alerts/{alert_id}/acknowledge", response_model=Acknowledgement)
    def acknowledge_alert(alert_id: str) -> Acknowledgement:
        acknowledged_at = _utc_now()
        with _connect(database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE alerts
                SET status = 'acknowledged',
                    acknowledged_at = COALESCE(acknowledged_at, ?)
                WHERE id = ?
                """,
                (acknowledged_at, alert_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Alert not found")
            row = connection.execute(
                "SELECT id, status, acknowledged_at FROM alerts WHERE id = ?",
                (alert_id,),
            ).fetchone()
        return Acknowledgement(
            alert_id=row["id"],
            status=row["status"],
            acknowledged_at=datetime.fromisoformat(row["acknowledged_at"]),
        )

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
