"""Contextual controls, separate from the calibrated IEEE model probability."""

import math

FACTOR_COVERAGE = [
    {
        "id": "amount",
        "name": "Amount anomalies",
        "status": "trained",
        "description": "Past-only seven-day amount ratio and z-score; small-charge sequence count.",
    },
    {
        "id": "velocity",
        "name": "Transaction velocity",
        "status": "trained",
        "description": "Strictly earlier transaction counts in one hour, one day and seven days. Login failures are a separate contextual control.",
    },
    {
        "id": "location",
        "name": "Location & travel",
        "status": "context",
        "description": "Provided coordinates and country mismatches. IEEE anonymized distance is a proxy, not verified GPS.",
    },
    {
        "id": "device",
        "name": "Device changes",
        "status": "partial",
        "description": "Device-type novelty is trained. Physical device sharing needs a supplied synthetic device identifier.",
    },
    {
        "id": "time",
        "name": "Time patterns",
        "status": "trained",
        "description": "Cyclic relative time and unseen hours versus prior history. IEEE time is not verified local time.",
    },
    {
        "id": "merchant",
        "name": "Merchant risk",
        "status": "context",
        "description": "Synthetic merchant-category review control; IEEE ProductCD is not a merchant category code.",
    },
    {
        "id": "account",
        "name": "Account behaviour",
        "status": "context",
        "description": "Recent password changes, new payees and withdrawals are provided scenario context, absent from IEEE.",
    },
    {
        "id": "network",
        "name": "Network links",
        "status": "context",
        "description": "Counts distinct accounts sharing the supplied device in prior request history. Not a trained fraud-ring model.",
    },
    {
        "id": "identity",
        "name": "Identity mismatches",
        "status": "partial",
        "description": "Email-domain comparisons and anonymized checkout matches are trained. Verified identity and disposable-email flags are contextual.",
    },
]


def controls(current, history, context):
    history = [event for event in history if event["time_offset"] < current["time_offset"]]
    same = [
        event
        for event in history
        if current.get("account_id") and event.get("account_id") == current["account_id"]
    ]
    findings = []

    def add(factor, title, decision, evidence):
        findings.append(
            {
                "factor": factor,
                "title": title,
                "decision": decision,
                "evidence": evidence,
                "source": "contextual control; not model training",
            }
        )

    if current.get("amount_ratio_7d", 1) >= 5 and current.get("transactions_7d", 0) >= 3:
        add(
            "amount",
            "Amount is at least 5× the prior average",
            "review",
            f"Ratio {current['amount_ratio_7d']:.1f}× across earlier seven-day transactions",
        )
    if current.get("small_charges_10m", 0) >= 4:
        add(
            "velocity",
            "Repeated small test charges",
            "review",
            f"{int(current['small_charges_10m'])} earlier charges of $5 or less in ten minutes",
        )
    if current.get("transactions_1h", 0) >= 8:
        add(
            "velocity",
            "Transaction burst",
            "review",
            f"{int(current['transactions_1h'])} earlier transactions in one hour",
        )
    if current.get("unusual_hour"):
        add(
            "time",
            "Previously unseen hour",
            "review",
            "At least five prior transactions, with none in this hour over seven days",
        )
    if current.get("device_type_new"):
        add(
            "device",
            "New device type",
            "review",
            "This device type was not present in the supplied prior seven-day history",
        )
    if (
        context.get("ip_country")
        and context.get("billing_country")
        and context["ip_country"] != context["billing_country"]
    ):
        add(
            "location",
            "IP and billing countries differ",
            "review",
            f"{context['ip_country']} versus {context['billing_country']}; travel and VPNs can be legitimate",
        )
    located = [
        event for event in same if event.get("latitude") is not None and event.get("longitude") is not None
    ]
    if located and context.get("latitude") is not None and context.get("longitude") is not None:
        previous = max(located, key=lambda event: event["time_offset"])
        a, b = math.radians(previous["latitude"]), math.radians(context["latitude"])
        dlat = b - a
        dlon = math.radians(context["longitude"] - previous["longitude"])
        hav = math.sin(dlat / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(dlon / 2) ** 2
        km = 6371 * 2 * math.asin(math.sqrt(min(1.0, max(0.0, hav))))
        hours = (current["time_offset"] - previous["time_offset"]) / 3600
        if km > 500 and km / hours > 900:
            add(
                "location",
                "Implausible travel speed",
                "block",
                f"{km:,.0f} km in {hours:.2f} hours; {km / hours:,.0f} km/h",
            )
    device = context.get("device_id")
    if device:
        shared = {
            event.get("account_id")
            for event in history
            if event.get("device_id") == device
            and event["time_offset"] >= current["time_offset"] - 86400
            and event.get("account_id")
        }
        shared.add(current.get("account_id"))
        shared.discard(None)
        if len(shared) >= 4:
            add(
                "network",
                "Device shared across accounts",
                "review",
                f"{len(shared)} distinct synthetic accounts in the last day; shared devices are not proof of a fraud ring",
            )
        known = {event.get("device_id") for event in same if event.get("device_id")}
        if known and device not in known:
            add(
                "device",
                "Unseen physical-device identifier",
                "review",
                "Device identifier not present in this account's supplied prior history",
            )
    if context.get("merchant_category") in ["gift_cards", "crypto", "gambling"]:
        add(
            "merchant",
            "Elevated merchant-category review",
            "review",
            context["merchant_category"] + " is a scenario policy assumption, not a learned IEEE category",
        )
    if context.get("failed_logins_1h", 0) >= 5:
        add(
            "account",
            "Repeated login failures",
            "review",
            f"{context['failed_logins_1h']} supplied login failures in one hour",
        )
    password = context.get("password_changed_minutes")
    if password is not None and password <= 30 and current["amount"] >= 500:
        add(
            "account",
            "Large payment after password change",
            "review",
            f"Password changed {password} minutes ago; payment ${current['amount']:,.2f}",
        )
    if context.get("new_payee") and context.get("withdrawal"):
        add(
            "account",
            "Withdrawal to a new payee",
            "review",
            "Both flags were provided by the synthetic scenario",
        )
    if context.get("identity_match") is False:
        add(
            "identity",
            "Identity verification mismatch",
            "review",
            "Supplied identity_match=false; no real identity verification service is connected",
        )
    if context.get("disposable_email"):
        add(
            "identity",
            "Disposable-email flag",
            "review",
            "A synthetic disposable-email signal was supplied; domains are not verified externally",
        )
    return findings


def combine(model_decision, findings):
    severity = {"approve": 0, "review": 1, "block": 2}
    return max([model_decision, *[item["decision"] for item in findings]], key=severity.get)
