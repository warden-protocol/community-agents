from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Signal:
    name: str
    severity: str  # low | medium | high
    details: str


def _severity_to_points(severity: str) -> int:
    return {"low": 10, "medium": 25, "high": 45}.get(severity, 10)


def check_tx_spike(tx_count: int, baseline: int) -> Optional[Signal]:
    if baseline > 0 and tx_count >= baseline * 3:
        return Signal(
            name="tx_spike",
            severity="medium",
            details=f"tx count spiked: {tx_count} vs baseline {baseline}",
        )
    return None


def check_large_outflow(total_outflow_usd: float, threshold_usd: float = 250_000) -> Optional[Signal]:
    if total_outflow_usd >= threshold_usd:
        return Signal(
            name="large_outflow",
            severity="high",
            details=f"large outflow ~",
        )
    return None


def score_signals(signals: List[Signal]) -> int:
    score = sum(_severity_to_points(s.severity) for s in signals)
    return max(0, min(100, score))


def recommended_actions(signals: List[Signal]) -> List[str]:
    if not signals:
        return ["no anomalies detected, continue monitoring"]

    actions = ["review onchain activity immediately"]
    for s in signals:
        if s.severity == "high":
            actions.append("treat as high risk, consider pausing integrations")

    return list(dict.fromkeys(actions))
