"""Authored synthetic cases. No competition records are used in the public replay."""

from copy import deepcopy


def scenarios():
    now = 10 * 86400 + 12 * 3600
    history = [
        {
            "account_id": "demo-account",
            "amount": float(65 + i),
            "time_offset": now - (8 - i) * 86400,
            "device_type": "desktop",
            "payer_email_domain": "gmail.com",
            "device_id": "known-device",
            "latitude": 3.139,
            "longitude": 101.687,
        }
        for i in range(7)
    ]
    base = {
        "transaction_id": "SCENARIO-NORMAL",
        "account_id": "demo-account",
        "amount": 75.0,
        "time_offset": now,
        "product": "W",
        "network": "visa",
        "card_type": "debit",
        "distance": 10.0,
        "identity_present": True,
        "device_type": "desktop",
        "payer_email_domain": "gmail.com",
        "receiver_email_domain": "gmail.com",
        "address_region": 87.0,
        "issuer_region": 150.0,
        "history": history,
        "context": {
            "device_id": "known-device",
            "country": "MY",
            "ip_country": "MY",
            "billing_country": "MY",
            "latitude": 3.139,
            "longitude": 101.687,
        },
        "benchmark_signals": {
            "C1": 3.0,
            "C2": 2.0,
            "C4": 0.0,
            "C6": 2.0,
            "C8": 0.0,
            "C10": 0.0,
            "C11": 2.0,
            "C12": 0.0,
            "C13": 8.0,
            "C14": 2.0,
            "D1": 90.0,
            "D2": 30.0,
            "D3": 1.0,
            "D4": 90.0,
            "D10": 90.0,
            "D15": 90.0,
            "M1": "T",
            "M2": "T",
            "M3": "T",
            "M5": "F",
            "M6": "T",
            "M7": "F",
            "M8": "F",
            "M9": "T",
        },
    }
    output = []

    def case(identifier, title, description, expected_factor=None):
        item = {
            "id": identifier,
            "title": title,
            "description": description,
            "expected_factor": expected_factor,
            "provenance": "Authored synthetic operational scenario",
            "transaction": deepcopy(base),
        }
        item["transaction"]["transaction_id"] = "SCENARIO-" + identifier.upper()
        output.append(item)
        return item["transaction"]

    case(
        "normal", "Everyday purchase", "A familiar amount, device and time, with a consistent prior history."
    )
    item = case(
        "amount",
        "Unusual purchase amount",
        "A $1,200 purchase after a history of roughly $70 payments.",
        "amount",
    )
    item["amount"] = 1200.0
    item = case(
        "card-testing",
        "Small charges in a burst",
        "Six small charges arrive within ten minutes before another purchase.",
        "velocity",
    )
    item["history"] += [
        {
            "account_id": "demo-account",
            "amount": 1.0,
            "time_offset": now - 30 * (i + 1),
            "device_type": "desktop",
            "payer_email_domain": "gmail.com",
            "device_id": "known-device",
        }
        for i in range(6)
    ]
    item = case(
        "impossible-travel",
        "Malaysia to Brazil in one hour",
        "Coordinates in the supplied history imply an implausible travel speed.",
        "location",
    )
    item["history"].append(history[-1] | {"time_offset": now - 3600})
    item["context"].update({"latitude": -23.5505, "longitude": -46.6333, "country": "BR", "ip_country": "BR"})
    item = case(
        "country-mismatch",
        "IP and billing mismatch",
        "An illustrative Brazilian IP country differs from the Malaysian billing country.",
        "location",
    )
    item["context"]["ip_country"] = "BR"
    item = case(
        "new-device",
        "First mobile-device purchase",
        "The account's supplied history contains only a different device and device type.",
        "device",
    )
    item["device_type"] = "mobile"
    item["context"]["device_id"] = "unseen-device"
    item = case(
        "odd-hour",
        "A purchase at 3 a.m.",
        "Previous transactions occur at noon; the new transaction arrives at an unseen relative hour.",
        "time",
    )
    item["time_offset"] = 10 * 86400 + 3 * 3600
    item = case(
        "merchant",
        "Gift-card purchase",
        "A supplied gift-card category triggers an explicit review policy.",
        "merchant",
    )
    item["context"]["merchant_category"] = "gift_cards"
    item = case(
        "account-takeover",
        "Password change, then withdrawal",
        "Repeated login failures and a recent password change precede a new-payee withdrawal.",
        "account",
    )
    item["amount"] = 1000.0
    item["context"].update(
        {"failed_logins_1h": 7, "password_changed_minutes": 5, "new_payee": True, "withdrawal": True}
    )
    item = case(
        "shared-device",
        "One device, five accounts",
        "A supplied device identifier links this account with four earlier synthetic accounts.",
        "network",
    )
    item["context"]["device_id"] = "shared-device"
    item["history"] += [
        {
            "account_id": f"other-account-{i}",
            "amount": 30.0,
            "time_offset": now - (i + 1) * 600,
            "device_id": "shared-device",
        }
        for i in range(4)
    ]
    item = case(
        "identity",
        "Identity and email warning",
        "Supplied identity mismatch and disposable-email flags trigger review; no identity service is connected.",
        "identity",
    )
    item["context"].update({"identity_match": False, "disposable_email": True})
    item["payer_email_domain"] = "throwaway.invalid"
    return output
