# MedGuard AI

**A synthetic-data-only healthcare IoT telemetry monitoring and security-alert demonstration.**

> **Hackathon submission metadata:** Selected track: **Cyber in Healthcare**. Challenge framing: **Secure Healthcare IoT Telemetry Monitoring** (a project-defined title for this starter, not an asserted ASTRA challenge number). Team: **MedGuard AI Team**. Replace this framing with the exact organizer-issued challenge number/title and actual team roster before submitting.

## Problem statement

Healthcare environments depend on connected monitoring devices and networked clinical systems. Unexpected device identities, unusual network origins, and out-of-range readings can be signs that deserve investigation. A useful prototype should make these signals visible without connecting to real clinical infrastructure or treating an automated score as a clinical decision.

## Proposed solution

MedGuard AI accepts **synthetic device telemetry**, evaluates it with transparent rules, persists the demo events and alerts to a local SQLite database, and displays the results in a small dashboard. It is a hackathon demonstration, not a medical device, clinical decision-support system, intrusion-prevention product, or production security control.

## Key features

- FastAPI endpoints for service health, telemetry, alerts, alert acknowledgement, and a deterministic anomaly simulation.
- Human-readable rules for unregistered device IDs, unexpected network labels, and illustrative out-of-range measurements.
- Local SQLite storage; no cloud service, external API, authentication service, or real patient records.
- Lightweight HTML/CSS/JavaScript dashboard served by the same-origin API.
- Pytest coverage for rule evaluation, API behavior, invalid input, and alert acknowledgement.
- Explicit safety boundaries: alerts are advisory, and the demo never blocks devices or modifies clinical systems.

## Technology stack

| Area | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI, Pydantic, Uvicorn |
| Frontend | HTML5, CSS3, browser JavaScript |
| Storage | SQLite via Python standard library |
| Tests | pytest, FastAPI TestClient, HTTPX |

## System architecture and data flow

1. The browser loads the static dashboard from the FastAPI service.
2. The dashboard fetches synthetic telemetry and alerts from same-origin `/api` endpoints.
3. A telemetry submission is validated, evaluated by the deterministic security rules, and stored with any resulting alerts in SQLite.
4. A security reviewer can acknowledge an alert. Acknowledgement records review state; it does not contain or imply a clinical decision.
5. **Simulate anomaly** submits a fixed, non-personal synthetic event. It does not generate network traffic or interact with medical equipment.

The Mermaid architecture specification is in [`docs/architecture_diagram.md`](docs/architecture_diagram.md). The structured STRIDE analysis is in [`docs/threat_model.md`](docs/threat_model.md).

## Setup and installation

Prerequisites: Python 3.10 or newer and pip.

From the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r src\backend\requirements.txt
Copy-Item .env.example .env
python -m src.backend.main
```

Open <http://127.0.0.1:8000/>. The API schema is at <http://127.0.0.1:8000/docs>.
The launcher reads `PORT` and `DATABASE_URL` from `.env` and binds only to `127.0.0.1`.

`DATABASE_URL` supports local SQLite URLs of the form `sqlite:///./medguard.db`. The database file is created on first run and is ignored by Git. This starter intentionally supports SQLite only. The example `SECRET_KEY` is reserved configuration and is **not used for authentication or encryption**; this demo has no authentication. Do not expose it or the unauthenticated service to a network.

Run the tests from the repository root:

```powershell
python -m pytest -q
```

The dashboard and API use the configured database and keep alert history across restarts. To start with a clean demo, stop the service and remove only the local `medguard.db` file (or set `DATABASE_URL` to another SQLite file).

## Simulated testing and evidence

The test suite checks:

- Normal readings do not trigger the threshold rules.
- Low synthetic oxygen saturation and an unregistered device are detected.
- Health, telemetry, alert, and simulated-anomaly API paths return the expected response shapes.
- Invalid telemetry is rejected and alerts can be acknowledged.

Verified in this workspace: `python -m pytest -q` completed with **8 passed**. Test results can vary by Python environment; no benchmark, hospital deployment, clinical validation, or real-world detection rate is claimed here. The seeded dashboard data and **Simulate anomaly** result are synthetic demonstration evidence, not evidence of a real attack.

## AI/ML model details

**No AI or machine-learning model is included.** Detection is a deterministic, explainable rules engine in [`src/backend/security_engine.py`](src/backend/security_engine.py). It checks an allowlisted set of synthetic device IDs and network labels and illustrative measurement thresholds. There is no trained model, training pipeline, inference service, or real-world dataset. The sample data is generated in code and contains no patient identity.

Threshold-based alerts can produce false positives because legitimate clinical variation, device calibration, and deployment context are not modeled. Rules and thresholds are for demonstration only and are not clinically validated. A qualified human security reviewer must independently investigate alerts; no automated finding should be treated as proof of compromise or as a basis for patient-care decisions.

## Limitations and safety declarations

- Synthetic data only: the application does not request, store, or need patient names, identifiers, records, or real medical-device telemetry.
- No real hospital attacks: the anomaly action submits one local synthetic API event. It does not scan, exploit, authenticate to, or send traffic to external or clinical systems.
- No authentication, authorization, multi-user controls, transport security, audit-grade integrity, or production hardening is implemented.
- SQLite is suitable here only for local demonstration. The application is not designed or validated for clinical, regulated, or production workloads.
- Detection coverage is narrow and static. No clinical interpretation, automated blocking, or patient-care action is performed.
- Bind to `127.0.0.1` for the demonstration. Do not connect this starter to a hospital network or deploy it with real data.

## Team and role breakdown

Team name: **MedGuard AI Team**. The following are role assignments, not claims about named participants:

| Role | Responsibility |
|---|---|
| Backend and security engineering | API, SQLite storage, rule evaluation, and safety boundaries |
| Frontend engineering | Dashboard, telemetry visualization, and alert acknowledgement |
| Testing and documentation | Automated tests, setup guidance, and threat-model documentation |

Add actual participant names and confirm role assignments before a formal submission.

## Open-source license and third-party components

This project is released under the MIT License; see [`LICENSE`](LICENSE). Runtime dependencies are FastAPI, Pydantic, Uvicorn, and python-dotenv. Test dependencies are pytest and HTTPX. Python's standard-library `sqlite3` module provides database access. Review each dependency's license and version before redistribution or deployment; no third-party assets or hosted services are bundled.

The small [`public/favicon.ico`](public/favicon.ico) file is the browser-tab icon for the dashboard; it contains only a generic shield mark.