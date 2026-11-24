import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.119.0";
import corpus from "./corpus.json" with { type: "json" };
import { validate, messages, citationCheck, freeModel } from "./core.mjs";

const db = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  { auth: { persistSession: false } },
);
const headers = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const reply = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { headers, status });
async function budget(scope: string, limit: number) {
  const { data, error } = await db.rpc("claim_budget", {
    p_scope: scope,
    p_limit: limit,
  });
  if (error) throw new Error("Budget service unavailable.");
  return data === true;
}
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers });
  if (req.method !== "POST") return reply({ error: "Use POST." }, 405);
  let input;
  try {
    if (Number(req.headers.get("content-length") ?? 0) > 8000)
      return reply({ error: "Request too large." }, 413);
    const raw = await req.text();
    if (new TextEncoder().encode(raw).length > 8000)
      return reply({ error: "Request too large." }, 413);
    input = validate(JSON.parse(raw), corpus);
  } catch {
    return reply(
      { error: "Invalid question, evidence selection or assessment." },
      400,
    );
  }
  const key =
    Deno.env.get("RAGS") ??
    Deno.env.get("OPENROUTER_API_KEY") ??
    Deno.env.get("rags");
  if (!key)
    return reply(
      {
        error:
          "The server-side OpenRouter key is not configured. Playbook guidance remains available.",
      },
      503,
    );
  try {
    if (!(await budget("fraudline-generation", 30)))
      return reply(
        {
          error:
            "The daily free assistant quota is reached. Your risk result and playbooks remain available.",
        },
        429,
      );
    const selected =
      Deno.env.get("FRAUDLINE_OPENROUTER_MODEL") ??
      "inclusionai/ling-3.2-flash:free";
    if (!freeModel(selected))
      return reply({ error: "Only free models are enabled." }, 503);
    let rateLimited = false;
    for (const candidate of [
      ...new Set([selected, "particle-ai/particle-1:free"]),
    ]) {
      try {
        const response = await fetch(
          "https://openrouter.ai/api/v1/chat/completions",
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${key}`,
              "Content-Type": "application/json",
              "HTTP-Referer": "https://fraudline.vercel.app",
              "X-Title": "Fraudline",
            },
            body: JSON.stringify({
              model: candidate,
              max_tokens: 3000,
              temperature: 0.1,
              reasoning: { exclude: true },
              provider: { max_price: { prompt: 0, completion: 0 } },
              messages: messages(input),
            }),
            signal: AbortSignal.timeout(25000),
          },
        );
        if (!response.ok) {
          console.warn("assistant_provider_http", candidate, response.status);
          rateLimited ||= response.status === 429;
          continue;
        }
        const data = await response.json(),
          answer = data.choices?.[0]?.message?.content;
        if (
          typeof answer !== "string" ||
          !answer.trim() ||
          answer.length > 12000 ||
          !citationCheck(answer, input.evidence.length)
        ) {
          console.warn(
            "assistant_output_rejected",
            candidate,
            typeof answer,
            answer?.length ?? 0,
            data.choices?.[0]?.finish_reason ?? "unknown",
          );
          continue;
        }
        return reply({
          status: input.evidence.length ? "answered" : "general_answer",
          answer,
          model: data.model ?? candidate,
          citations_valid: input.evidence.length > 0,
          general_explanation: input.evidence.length === 0,
        });
      } catch {
        console.warn("assistant_provider_timeout_or_network", candidate);
        /* Keep failures and provider messages private; try only one free fallback. */
      }
    }
    if (rateLimited)
      return reply(
        {
          error:
            "OpenRouter’s free service is rate-limited. Your risk result and playbooks remain available. Try again later; no paid fallback was used.",
        },
        429,
      );
    return reply(
      {
        error:
          "The free AI provider is unavailable or returned unverifiable citations. Your risk result and playbooks remain available. Try again later.",
      },
      503,
    );
  } catch {
    return reply(
      {
        error:
          "The assistant is temporarily unavailable. Your risk result and playbooks remain available.",
      },
      503,
    );
  }
});
