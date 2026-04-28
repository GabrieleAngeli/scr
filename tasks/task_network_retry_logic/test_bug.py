import pytest

from bug import fetch_with_retry


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def get(self, timeout):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return {"payload": outcome, "timeout": timeout}


def test_fetch_succeeds_after_retries() -> None:
    client = FakeClient([TimeoutError("slow"), TimeoutError("slow again"), "ok"])

    result = fetch_with_retry(client, retries=3, timeout_seconds=2.5)

    assert result["payload"] == "ok"
    assert client.calls == 3


def test_fetch_raises_after_all_retries_are_consumed() -> None:
    client = FakeClient([TimeoutError("first"), TimeoutError("second")])

    with pytest.raises(TimeoutError):
        fetch_with_retry(client, retries=2, timeout_seconds=1.0)

    assert client.calls == 2
