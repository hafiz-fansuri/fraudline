import test from "node:test";
import assert from "node:assert/strict";
import {
  validate,
  freeModel,
  citationCheck,
  messages,
} from "../supabase/functions/fraudline-assistant/core.mjs";
const corpus = [
  {
    id: "general",
    title: "Human review",
    content: "A score is not a verdict.",
  },
];
const body = {
  question: "What does review mean?",
  evidence_ids: ["general"],
  assessment: {
    decision: "review",
    model_decision: "approve",
    probability: 0.02,
    account_id: "PRIVATE-ID",
    amount: 900,
  },
};
test("only allowlisted assessment fields reach the provider", () => {
  const value = validate(body, corpus);
  assert.deepEqual(Object.keys(value.assessment), [
    "decision",
    "model_decision",
    "probability",
  ]);
  assert.ok(!JSON.stringify(messages(value)).includes("PRIVATE-ID"));
});
test("evidence IDs resolve to canonical passages, not caller prose", () => {
  assert.throws(() =>
    validate({ ...body, evidence_ids: ["injected"] }, corpus),
  );
  assert.throws(() =>
    validate({ ...body, evidence_ids: ["general", "general"] }, corpus),
  );
  assert.equal(validate(body, corpus).evidence[0].content, corpus[0].content);
});
test("free-only model selection and citation bounds", () => {
  assert.ok(freeModel("openrouter/free"));
  assert.ok(freeModel("vendor/model:free"));
  assert.ok(!freeModel("vendor/paid"));
  assert.ok(citationCheck("Check evidence [1]", 1));
  assert.ok(!citationCheck("Invented [2]", 1));
  assert.ok(!citationCheck("No citations", 1));
  assert.ok(citationCheck("General explanation", 0));
  assert.ok(!citationCheck("Invented [1]", 0));
});
test("invalid question, probability and status are rejected", () => {
  assert.throws(() => validate({ ...body, question: "x" }, corpus));
  assert.throws(() =>
    validate(
      { ...body, assessment: { ...body.assessment, probability: NaN } },
      corpus,
    ),
  );
  assert.throws(() =>
    validate(
      { ...body, assessment: { ...body.assessment, decision: "transfer" } },
      corpus,
    ),
  );
});
