import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from fraudline.api import Transaction
from fraudline.history import enrich, history_features
from fraudline.scenarios import scenarios
from fraudline.signals import combine, controls


def test_history_excludes_current_equal_time_and_future():
    frame = pd.DataFrame(
        {
            "account_id": ["a"] * 5,
            "amount": [10.0, 20.0, 900.0, 999.0, 30.0],
            "time_offset": [0, 100, 100, 200, 300],
        }
    )
    result = history_features(frame)
    assert result.loc[1, "transactions_1h"] == result.loc[2, "transactions_1h"] == 1
    assert result.loc[1, "amount_ratio_7d"] == 2
    assert result.loc[2, "amount_ratio_7d"] == 90
    assert result.loc[0, "transactions_1h"] == 0


def test_offline_online_history_parity_and_account_isolation():
    history = [
        {"account_id": "a", "amount": 10.0, "time_offset": 0},
        {"account_id": "b", "amount": 999.0, "time_offset": 100},
    ]
    current = {"account_id": "a", "amount": 30.0, "time_offset": 200}
    expected = history_features(pd.DataFrame([*history, current])).iloc[-1]
    actual = enrich(current, list(reversed(history)))
    for name, value in expected.items():
        assert np.isclose(actual[name], value)
    assert actual["transactions_24h"] == 1 and actual["amount_ratio_7d"] == 3


@pytest.mark.parametrize("case", scenarios(), ids=lambda case: case["id"])
def test_synthetic_factor_scenarios(case):
    event = Transaction.model_validate(case["transaction"]).model_dump()
    values = enrich(event, event["history"])
    findings = controls(values, event["history"], event["context"])
    if case["expected_factor"]:
        assert case["expected_factor"] in [item["factor"] for item in findings]
    else:
        assert findings == []
    assert combine("block", findings) == "block"
    if case["id"] == "impossible-travel":
        assert combine("approve", findings) == "block"


def test_future_history_cannot_create_travel_alert():
    current = {"account_id": "a", "amount": 20.0, "time_offset": 100}
    future = [{"account_id": "a", "amount": 20.0, "time_offset": 200, "latitude": 50.0, "longitude": 100.0}]
    assert controls(current, future, {"latitude": -20.0, "longitude": -40.0}) == []


@pytest.mark.parametrize("values", [{"C1": "T"}, {"M1": 4}, {"isFraud": 1}, {"D1": -2}])
def test_reject_invalid_benchmark_signals(values):
    with pytest.raises(ValidationError):
        Transaction.model_validate(scenarios()[0]["transaction"] | {"benchmark_signals": values})
