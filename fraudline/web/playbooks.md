# Investigation playbooks

Illustrative demo guidance, not bank-approved policy.

<a id="amount"></a>

## Amount and velocity

Compare the payment amount with strictly earlier activity. Check repeated small charges and rapid transaction bursts. Ask an analyst to confirm context before escalating. An unusual amount alone does not establish fraud.

Next: Review earlier activity and contact the customer through an established channel.

Revision: bank-playbooks-2026-11-24; SHA-256: `6062a2a22ab6eb58aad69ee8557ebeb20769233487b61e23c77364eb61afda22`

<a id="velocity"></a>

## Card testing and bursts

Repeated small test charges or a transaction burst warrant review of earlier activity and linked attempts. Confirm timestamps and duplicates. Do not infer an attack solely from transaction count.

Next: Check duplicates and the sequence of earlier attempts.

Revision: bank-playbooks-2026-11-24; SHA-256: `69cd3866ea7ba17dca8042b4837df6bcb8bcdd84a89235785a0c7c3ec7efe133`

<a id="location"></a>

## Location and travel

An IP and billing-country mismatch can reflect travel or a VPN. Implausible travel requires reliable coordinates and timestamps. Verify location quality and use established customer verification before a final decision.

Next: Verify location quality and confirm travel through an established channel.

Revision: bank-playbooks-2026-11-24; SHA-256: `fd62736cda53742fae3f39a64e998e6da9b75269acd3d5386358fa178685fb0d`

<a id="device"></a>

## Device changes

A new device type or identifier is a review signal. Shared devices can be legitimate. Check prior device history and authentication evidence before deciding that an account is compromised.

Next: Compare device history and verify the recent authentication.

Revision: bank-playbooks-2026-11-24; SHA-256: `5945b7f783f30516212afa98859349ab3397e548d4075a1fcc36e5886c71e13b`

<a id="account"></a>

## Account takeover

A password change followed by a large payment, a new payee followed by withdrawal, or repeated login failures warrants account review. Confirm event order. Never ask for passwords or one-time codes.

Next: Review authentication and payee changes; escalate through the institution's approved process.

Revision: bank-playbooks-2026-11-24; SHA-256: `5cf0eca4817eaf713c13bb12c16780a77ee18112abeaea6f5e9fa1705ed3b850`

<a id="network"></a>

## Shared-device links

Several accounts using one device can warrant linked-account review, but households and shared terminals are legitimate explanations. A graph link is an association, not proof of a fraud ring.

Next: Inspect linked activity and record alternative explanations.

Revision: bank-playbooks-2026-11-24; SHA-256: `4e0cb92590af474c1cc752fa5c88fa2cdb764cb99153736f3bf0b2212e5d0ffc`

<a id="identity"></a>

## Identity checks

An identity mismatch or disposable-email flag warrants checking source reliability. Email domains are weak proxies for identity. Use the institution's approved verification process; never collect identity documents in this public demo.

Next: Verify the source of the mismatch using the approved identity workflow.

Revision: bank-playbooks-2026-11-24; SHA-256: `4db3b38b23dd08e74315af18d137b8a9ad2ade144f3947a1b341f7dbd5ec9cfe`

<a id="merchant"></a>

## Merchant context

Gift cards, crypto and gambling are illustrative review categories in this demo. They are not universal prohibited categories or learned IEEE merchant labels. Apply only an institution-approved merchant policy.

Next: Check the institution's merchant policy and the customer's context.

Revision: bank-playbooks-2026-11-24; SHA-256: `82489bfa533b7f619a321c59d5f006305507edd7c740cc1d5e9d0ccac93f3844`

<a id="time"></a>

## Time patterns

An unusual hour is a review cue, not proof of fraud. IEEE TransactionDT is relative time and does not establish a customer's local time zone. Confirm the event time and earlier behavior.

Next: Confirm the time zone and compare strictly earlier activity.

Revision: bank-playbooks-2026-11-24; SHA-256: `1b59730b74ea4dd17162aee474abaae58b438fab8156a4e065870e09e363b6e0`

<a id="general"></a>

## Human review and evidence

Keep the calibrated model probability separate from contextual control findings. A model score is not a verdict. Record the model version, missing inputs and cited evidence. A person must approve consequential action; the assistant cannot block funds or declare regulatory compliance.

Next: Review missing information and record the human decision in the bank's case system.

Revision: bank-playbooks-2026-11-24; SHA-256: `dcd4518f8236cd0b6edf6dbb1a03d343b16a311dcb3cde48e272e0fac3e563f6`

