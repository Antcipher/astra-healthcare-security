# Architecture diagram

Textual Mermaid specification for the architecture diagram (used instead of a binary PNG so the diagram remains reviewable and version-controlled):

```mermaid
flowchart LR
    Browser["Browser dashboard<br/>HTML / CSS / JavaScript"]
    API["FastAPI application<br/>same-origin /api"]
    Validation["Pydantic input validation"]
    Engine["Deterministic rules engine<br/>synthetic telemetry only"]
    DB[("Local SQLite<br/>synthetic events and alerts")]
    Reviewer["Human security reviewer<br/>acknowledges alerts"]
    Simulator["Simulate anomaly<br/>fixed synthetic event"]

    Browser -->|"GET dashboard and assets"| API
    Browser -->|"GET health / telemetry / alerts"| API
    Browser -->|"POST synthetic telemetry"| API
    Simulator -->|"POST /api/simulate/anomaly"| API
    API --> Validation
    Validation --> Engine
    Engine -->|"findings for review"| API
    API <-->|"persist and query"| DB
    API -->|"events and alert status"| Browser
    Reviewer -->|"POST alert acknowledgement"| API
```

All components run locally. The simulator does not produce network traffic toward devices or third-party systems. The diagram describes a demonstration, not a deployment architecture for a healthcare environment.
