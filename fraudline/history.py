"""Event-time history features. Equal-time peers and future events are excluded."""

import numpy as np
import pandas as pd

HISTORY_FEATURES = [
    "history_available",
    "transactions_1h",
    "transactions_24h",
    "transactions_7d",
    "small_charges_10m",
    "amount_ratio_7d",
    "amount_zscore_7d",
    "seconds_since_previous",
    "unusual_hour",
    "device_type_new",
    "payer_domain_changed",
]


def history_features(frame):
    output = np.zeros((len(frame), len(HISTORY_FEATURES)), dtype="float32")
    output[:, 5] = 1
    output[:, 7] = -1
    if "account_id" not in frame:
        return pd.DataFrame(output, index=frame.index, columns=HISTORY_FEATURES)
    valid = frame[frame.account_id.notna()].sort_values(["account_id", "time_offset"], kind="stable")
    for _, group in valid.groupby("account_id", sort=False):
        t = group.time_offset.to_numpy(dtype=float)
        amount = group.amount.to_numpy(dtype=float)
        upper = np.searchsorted(t, t, side="left")
        cumulative = np.r_[0.0, np.cumsum(amount)]
        squares = np.r_[0.0, np.cumsum(amount * amount)]
        small = np.r_[0.0, np.cumsum(amount <= 5)]
        values = np.zeros((len(group), len(HISTORY_FEATURES)))
        values[:, 0] = 1
        for column, window in [(1, 3600), (2, 86400), (3, 604800)]:
            lower = np.searchsorted(t, t - window, side="left")
            values[:, column] = upper - lower
        lower = np.searchsorted(t, t - 604800, side="left")
        count = upper - lower
        mean = (cumulative[upper] - cumulative[lower]) / np.maximum(count, 1)
        variance = np.maximum(0, (squares[upper] - squares[lower]) / np.maximum(count, 1) - mean * mean)
        values[:, 4] = small[upper] - small[np.searchsorted(t, t - 600, side="left")]
        values[:, 5] = np.where(count > 0, amount / np.maximum(mean, 0.01), 1)
        values[:, 6] = np.where(count >= 2, (amount - mean) / np.maximum(np.sqrt(variance), 1), 0)
        previous = np.maximum(upper - 1, 0)
        values[:, 7] = np.where(upper > 0, t - t[previous], -1)
        hours = ((t % 86400) // 3600).astype(int)
        for hour in np.unique(hours):
            subset = t[hours == hour]
            seen = np.searchsorted(subset, t, "left") - np.searchsorted(subset, t - 604800, "left")
            mask = hours == hour
            values[mask, 8] = ((seen == 0) & (count >= 5))[mask]
        if "device_type" in group:
            devices = group.device_type.fillna("unknown").to_numpy()
            for device in np.unique(devices):
                if device == "unknown":
                    continue
                subset = t[devices == device]
                seen = np.searchsorted(subset, t, "left") - np.searchsorted(subset, t - 604800, "left")
                mask = devices == device
                values[mask, 9] = ((seen == 0) & (count > 0))[mask]
        if "payer_email_domain" in group:
            domains = group.payer_email_domain.fillna("").to_numpy()
            values[:, 10] = (
                (upper > 0) & (domains != "") & (domains[previous] != "") & (domains != domains[previous])
            )
        output[frame.index.get_indexer(group.index)] = values
    return pd.DataFrame(output, index=frame.index, columns=HISTORY_FEATURES)


def enrich(current, history):
    # Request history is illustrative input in this demo; a production gateway must supply trusted history.
    earlier = [event for event in history if event["time_offset"] < current["time_offset"]]
    rows = pd.DataFrame([*earlier, current])
    return current | history_features(rows).iloc[-1].to_dict()
