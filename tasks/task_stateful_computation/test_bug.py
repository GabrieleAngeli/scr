from bug import RunningLedger


def test_running_total_accumulates_positive_and_negative_amounts() -> None:
    ledger = RunningLedger()

    assert ledger.apply(10) == 10
    assert ledger.apply(5) == 15
    assert ledger.apply(-3) == 12


def test_snapshot_preserves_total_and_history() -> None:
    ledger = RunningLedger()
    ledger.apply(4)
    ledger.apply(6)

    assert ledger.snapshot() == {
        "total": 10,
        "history": [4, 6],
    }
