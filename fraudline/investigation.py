"""Bounded investigation planner and evidence retrieval, ported from Proofline.

Rank fusion, two-pass source diversity, citation validation and abstention mirror
Proofline core.mjs. The bank demo uses local authored playbooks, not OWASP as a
fraud policy. No customer data, external tools, model keys or paid service needed.
"""

import hashlib
import re
from pathlib import Path

VERSION = "bank-playbooks-2026-11-24"
PLAYBOOKS = [
    (
        "amount",
        "Amount and velocity",
        "Compare the payment amount with strictly earlier activity. Check repeated small charges and rapid transaction bursts. Ask an analyst to confirm context before escalating. An unusual amount alone does not establish fraud.",
        "Review earlier activity and contact the customer through an established channel.",
    ),
    (
        "velocity",
        "Card testing and bursts",
        "Repeated small test charges or a transaction burst warrant review of earlier activity and linked attempts. Confirm timestamps and duplicates. Do not infer an attack solely from transaction count.",
        "Check duplicates and the sequence of earlier attempts.",
    ),
    (
        "location",
        "Location and travel",
        "An IP and billing-country mismatch can reflect travel or a VPN. Implausible travel requires reliable coordinates and timestamps. Verify location quality and use established customer verification before a final decision.",
        "Verify location quality and confirm travel through an established channel.",
    ),
    (
        "device",
        "Device changes",
        "A new device type or identifier is a review signal. Shared devices can be legitimate. Check prior device history and authentication evidence before deciding that an account is compromised.",
        "Compare device history and verify the recent authentication.",
    ),
    (
        "account",
        "Account takeover",
        "A password change followed by a large payment, a new payee followed by withdrawal, or repeated login failures warrants account review. Confirm event order. Never ask for passwords or one-time codes.",
        "Review authentication and payee changes; escalate through the institution's approved process.",
    ),
    (
        "network",
        "Shared-device links",
        "Several accounts using one device can warrant linked-account review, but households and shared terminals are legitimate explanations. A graph link is an association, not proof of a fraud ring.",
        "Inspect linked activity and record alternative explanations.",
    ),
    (
        "identity",
        "Identity checks",
        "An identity mismatch or disposable-email flag warrants checking source reliability. Email domains are weak proxies for identity. Use the institution's approved verification process; never collect identity documents in this public demo.",
        "Verify the source of the mismatch using the approved identity workflow.",
    ),
    (
        "merchant",
        "Merchant context",
        "Gift cards, crypto and gambling are illustrative review categories in this demo. They are not universal prohibited categories or learned IEEE merchant labels. Apply only an institution-approved merchant policy.",
        "Check the institution's merchant policy and the customer's context.",
    ),
    (
        "time",
        "Time patterns",
        "An unusual hour is a review cue, not proof of fraud. IEEE TransactionDT is relative time and does not establish a customer's local time zone. Confirm the event time and earlier behavior.",
        "Confirm the time zone and compare strictly earlier activity.",
    ),
    (
        "general",
        "Human review and evidence",
        "Keep the calibrated model probability separate from contextual control findings. A model score is not a verdict. Record the model version, missing inputs and cited evidence. A person must approve consequential action; the assistant cannot block funds or declare regulatory compliance.",
        "Review missing information and record the human decision in the bank's case system.",
    ),
]


def sources():
    return [
        dict(
            id=key,
            document_id=key,
            title=title,
            content=text,
            next_step=step,
            publisher="Fraudline demo authors",
            version=VERSION,
            sha256=hashlib.sha256(text.encode()).hexdigest(),
            url=f"/assets/playbooks.md#{key}",
            status="Illustrative; not bank-approved policy",
        )
        for key, title, text, step in PLAYBOOKS
    ]


def fuse_ranks(channels, k=40):
    ranked = {}
    for rows in channels:
        for index, row in enumerate(rows):
            item = ranked.setdefault(row["id"], dict(row, score=0))
            item["score"] += 1 / (k + index + 1)
    return sorted(ranked.values(), key=lambda row: (-row["score"], row["id"]))


def retrieve(question, factors):
    words = set(re.findall(r"[a-z]{3,}", question.lower())) - set(
        "the and for how what this that with should does evidence human review steps apply transaction guidance selected current please find needs about".split()
    )
    corpus = sources()
    lexical = []
    for row in corpus:
        tokens = set(re.findall(r"[a-z]{3,}", (row["title"] + " " + row["content"]).lower()))
        overlap = len(words & tokens)
        if overlap:
            lexical.append((overlap, row))
    lexical.sort(key=lambda item: (-item[0], item[1]["id"]))
    control = [row for row in corpus if row["id"] in factors]
    if not words and len(question.strip()) < 8 and not factors:
        return []
    if not words:
        # Generic review questions must not manufacture unrelated risk factors.
        lexical = [(1, row) for row in corpus if row["id"] in factors or row["id"] == "general"]
    # Explicit control-channel matching, not an embedding/semantic claim.
    return fuse_ranks([[row for _, row in lexical], control])[:5]


def investigate(result, question):
    factors = sorted({s["factor"] for s in result["signals"]})
    evidence = retrieve(question, factors)
    plan = [
        dict(tool="inspect_scored_transaction", status="completed"),
        dict(tool="retrieve_playbooks", queries=[question, *factors], status="completed"),
        dict(tool="validate_citations", status="completed"),
    ]
    if not evidence:
        return dict(
            status="abstained",
            answer="The available playbooks do not establish an answer.",
            evidence=[],
            plan=plan,
            mode="bounded extractive RAG",
            citations_valid=False,
        )
    paragraphs = [f"{row['content']} [{i + 1}]" for i, row in enumerate(evidence[:3])]
    answer = "\n\n".join(paragraphs)
    ids = [int(i) for i in re.findall(r"\[(\d+)\]", answer)]
    return dict(
        status="evidence_ready",
        answer=answer,
        evidence=evidence,
        next_steps=[dict(text=row["next_step"], citation=i + 1) for i, row in enumerate(evidence[:3])],
        plan=plan,
        mode="bounded extractive RAG; no language model or external calls",
        citations_valid=bool(ids) and all(1 <= i <= len(evidence) for i in ids),
        corpus_version=VERSION,
        warning="Illustrative guidance. Replace with approved bank policies before operational use.",
    )


def export_playbooks():
    text = "# Investigation playbooks\n\nIllustrative demo guidance, not bank-approved policy.\n\n"
    for row in sources():
        text += f'<a id="{row["id"]}"></a>\n\n## {row["title"]}\n\n{row["content"]}\n\nNext: {row["next_step"]}\n\nRevision: {VERSION}; SHA-256: `{row["sha256"]}`\n\n'
    (Path(__file__).parent / "web/playbooks.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    export_playbooks()
