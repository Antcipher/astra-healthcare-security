from fastapi.testclient import TestClient

from src.backend.main import create_app
from src.backend.security_engine import evaluate_telemetry


def _event(
    device_id: str = "monitor-01",
    metric: str = "heart_rate",
    value: float = 72,
    source_network: str = "clinical-sim-net",
) -> dict[str, object]:
    return {
        "device_id": device_id,
        "metric": metric,
        "value": value,
        "source_network": source_network,
    }


def test_normal_synthetic_reading_has_no_findings() -> None:
    assert evaluate_telemetry(_event()) == []


def test_unknown_device_and_low_spo2_are_flagged() -> None:
    findings = evaluate_telemetry(
        _event(device_id="unknown-sim-01", metric="spo2", value=84)
    )
    assert {finding.rule_id for finding in findings} == {
        "unknown-device",
        "out-of-range-spo2",
    }
    assert all(finding.severity in {"medium", "high"} for finding in findings)


def test_unexpected_network_is_flagged() -> None:
    findings = evaluate_telemetry(_event(source_network="untrusted-sim-net"))
    assert [finding.rule_id for finding in findings] == ["unexpected-network"]


def test_api_health_and_seeded_data_are_synthetic(tmp_path) -> None:
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'health.db'}"))

    health = client.get("/api/health")
    telemetry = client.get("/api/telemetry")
    alerts = client.get("/api/alerts")

    assert health.status_code == 200
    assert health.json()["synthetic_data_only"] is True
    assert telemetry.status_code == 200
    assert telemetry.json()["synthetic"] is True
    assert len(telemetry.json()["items"]) == 4
    assert all(item["synthetic"] for item in telemetry.json()["items"])
    assert alerts.status_code == 200
    assert any(alert["rule_id"] == "out-of-range-spo2" for alert in alerts.json()["items"])


def test_dashboard_and_static_assets_are_served(tmp_path) -> None:
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'assets.db'}"))

    dashboard = client.get("/")
    script = client.get("/assets/app.js")
    favicon = client.get("/public/favicon.ico")

    assert dashboard.status_code == 200
    assert "MedGuard AI" in dashboard.text
    assert script.status_code == 200
    assert "refreshDashboard" in script.text
    assert favicon.status_code == 200
    assert favicon.headers["content-type"] == "image/x-icon"


def test_simulated_anomaly_persists_findings_and_can_be_acknowledged(tmp_path) -> None:
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'anomaly.db'}"))

    response = client.post("/api/simulate/anomaly")
    assert response.status_code == 201
    result = response.json()
    assert result["event"]["synthetic"] is True
    assert {alert["rule_id"] for alert in result["alerts"]} == {
        "unknown-device",
        "out-of-range-spo2",
    }

    alert_id = result["alerts"][0]["id"]
    acknowledged = client.post(f"/api/alerts/{alert_id}/acknowledge")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "acknowledged"
    stored = client.get("/api/alerts").json()["items"]
    assert next(alert for alert in stored if alert["id"] == alert_id)["status"] == "acknowledged"


def test_telemetry_validation_and_missing_alert(tmp_path) -> None:
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'validation.db'}"))

    invalid = client.post(
        "/api/telemetry",
        json={"device_id": "monitor-01", "metric": "patient_name", "value": 72},
    )
    personal_identifier = client.post(
        "/api/telemetry",
        json={"device_id": "real-patient-name", "metric": "heart_rate", "value": 72},
    )
    missing_alert = client.post("/api/alerts/not-a-real-id/acknowledge")

    assert invalid.status_code == 422
    assert personal_identifier.status_code == 422
    assert missing_alert.status_code == 404


def test_telemetry_submission_returns_expected_event_and_alerts(tmp_path) -> None:
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'submit.db'}"))

    response = client.post(
        "/api/telemetry",
        json={
            "device_id": "monitor-01",
            "metric": "heart_rate",
            "value": 170,
            "source_network": "clinical-sim-net",
        },
    )

    assert response.status_code == 201
    result = response.json()
    assert result["event"]["metric"] == "heart_rate"
    assert result["event"]["unit"] == "bpm"
    assert result["event"]["synthetic"] is True
    assert result["alerts"][0]["rule_id"] == "out-of-range-heart_rate"
