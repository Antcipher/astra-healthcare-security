# MedGuard AI threat model

## Scope and assumptions

This STRIDE review covers the local hackathon demonstration: a browser dashboard, same-origin FastAPI endpoints, a deterministic rule evaluator, and a local SQLite database containing synthetic telemetry and alerts. It does not model or authorize connection to an EHR, hospital network, medical device, or real patient data. The demo has no authentication and is intended to bind to loopback only.

### Assets

- Integrity and availability of the local demo process and SQLite file.
- Integrity of synthetic event and alert records.
- Confidentiality of local configuration and source files.
- Correct presentation of rule findings and acknowledgement state.

### Trust boundaries

1. Browser to API: all submitted fields are untrusted, even when submitted by the bundled dashboard.
2. API to SQLite: data is persisted locally; database file permissions and host security remain external responsibilities.
3. Demo operator to host: anyone able to access the local service or files may inspect or alter this non-authenticated demonstration.

## STRIDE analysis

| STRIDE category | Threat and affected assets | Risk | Mitigations in this starter | Residual risk / next step |
|---|---|---|---|---|
| Spoofing | A caller submits telemetry claiming a known device ID or network label. | A forged event could evade identity-based rules or create misleading alerts. | Strict input schema; known device/network labels are used only as transparent demo heuristics; findings remain advisory. | Labels are not cryptographic identity. Production use would require authenticated device identity, certificate lifecycle management, and user authentication. |
| Tampering | A local user or compromised process alters event/alert rows or source code. | Alert history and displayed findings could be changed. | Parameterized SQL; SQLite transactions; input validation; explicit local-only scope. | No tamper-evident audit log, signed records, file encryption, or database access control is provided. Protect the host and use an appropriate managed audit architecture for any real system. |
| Repudiation | An operator denies having acknowledged an alert or submitted a request. | The demo cannot provide reliable attribution. | Alert state is stored, but no identity or actor is asserted. | No authenticated actor, immutable audit trail, or trusted timestamping exists. Do not treat demo records as compliance evidence. |
| Information disclosure | Real patient information or secrets are entered into requests, database files, logs, or screenshots. | Sensitive data could be exposed locally or in shared artifacts. | Dashboard and seeded data are synthetic; input schema has no free-text patient fields; `.env` and local database files are gitignored; docs warn against real data. | The service cannot guarantee operators will not misuse it. Never submit real data or secrets; add formal access controls and privacy review before any broader use. |
| Denial of service | A client floods endpoints or submits excessive requests. | The local demo could become slow or unavailable. | Request fields and list limits are bounded; the demo binds to loopback in documented commands. | No authentication, rate limiting, concurrency quotas, or production availability controls. Do not expose it to untrusted networks. |
| Elevation of privilege | An unauthenticated caller accesses alert acknowledgement or API operations. | Callers can alter alert status and inspect demo data. | No claim of access control; operations are limited to synthetic demo data and documented for local use only. | There is no authentication or authorization. Implement identity, least privilege, CSRF protections where applicable, and security review before network exposure. |

## Healthcare IoT / EHR-specific considerations

- This demonstration does not integrate with or probe EHRs, gateways, or medical equipment.
- Unknown device IDs and network labels are illustrative indicators, not device attestation or network-segmentation enforcement.
- Measurement thresholds are demonstration rules and are not validated clinical limits.
- No finding authorizes blocking a device, changing treatment, or contacting a patient.
- Healthcare deployment would need clinical safety review, privacy impact assessment, threat-informed architecture, regulatory analysis, identity and key management, secure update procedures, monitoring, incident response, and appropriate validation.

## Secure use checklist

- Run on a trusted development machine bound to `127.0.0.1`.
- Use only synthetic test data; do not enter PHI, credentials, or other secrets.
- Keep `.env` and SQLite database files out of source control.
- Do not expose the service, port-forward it, or connect it to a clinical network.
- Treat all alerts as examples requiring qualified human review.
