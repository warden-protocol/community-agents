from src.agent.rules import (
    Signal,
    check_tx_spike,
    check_large_outflow,
    score_signals,
    recommended_actions,
)


def test_no_tx_spike():
    sig = check_tx_spike(tx_count=10, baseline=20)
    assert sig is None


def test_tx_spike_detected():
    sig = check_tx_spike(tx_count=100, baseline=20)
    assert sig is not None
    assert sig.name == "tx_spike"
    assert sig.severity == "medium"


def test_large_outflow_detected():
    sig = check_large_outflow(500_000)
    assert sig is not None
    assert sig.name == "large_outflow"
    assert sig.severity == "high"


def test_score_is_deterministic():
    signals = [
        Signal("tx_spike", "medium", "spike"),
        Signal("large_outflow", "high", "outflow"),
    ]
    score1 = score_signals(signals)
    score2 = score_signals(signals)
    assert score1 == score2


def test_no_false_positive_actions():
    actions = recommended_actions([])
    assert actions == ["no anomalies detected, continue monitoring"]
