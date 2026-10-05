"""Transparent, non-clinical security heuristics for synthetic telemetry."""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    severity: str
    description: str
    recommended_action: str


KNOWN_DEVICES = frozenset({"monitor-01", "pump-02", "gateway-01"})
KNOWN_NETWORKS = frozenset({"clinical-sim-net"})


def evaluate_telemetry(event: Mapping[str, object]) -> list[Finding]:
    """Return advisory findings; this function never blocks or changes a device."""
    findings: list[Finding] = []
    device_id = str(event["device_id"])
    network = str(event["source_network"])
    metric = str(event["metric"])
    value = float(event["value"])

    if device_id not in KNOWN_DEVICES:
        findings.append(
            Finding(
                rule_id="unknown-device",
                title="Unregistered simulated device",
                severity="high",
                description=f"Device {device_id!r} is not in the demonstration allowlist.",
                recommended_action="Verify the device identity and inventory with a security reviewer.",
            )
        )

    if network not in KNOWN_NETWORKS:
        findings.append(
            Finding(
                rule_id="unexpected-network",
                title="Unexpected simulated network",
                severity="medium",
                description=f"Network label {network!r} is not in the demonstration allowlist.",
                recommended_action="Check the expected network context with a security reviewer.",
            )
        )

    threshold = _threshold_finding(metric, value)
    if threshold is not None:
        findings.append(threshold)

    return findings


def _threshold_finding(metric: str, value: float) -> Finding | None:
    out_of_range = {
        "heart_rate": value < 40 or value > 150,
        "spo2": value < 90,
        "temperature_c": value > 39.5,
        "respiratory_rate": value < 8 or value > 30,
    }
    if not out_of_range.get(metric, False):
        return None

    return Finding(
        rule_id=f"out-of-range-{metric}",
        title="Illustrative measurement threshold exceeded",
        severity="medium",
        description=(
            f"The synthetic {metric} value {value:g} is outside this demo's "
            "illustrative rule threshold."
        ),
        recommended_action=(
            "Have a qualified reviewer validate the synthetic event and its context; "
            "this is not a clinical assessment."
        ),
    )
