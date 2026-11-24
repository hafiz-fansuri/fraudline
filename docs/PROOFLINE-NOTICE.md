# Proofline integration and license

The bounded investigation implementation adapts rank fusion, source diversity,
citation validation and abstention patterns from `hafiz-fansuri/proofline`, revision
`2bbf9bf3148abdef13d276f6694a3794ab047636`, especially `src/lib/core.mjs` and
`supabase/functions/proofline/index.ts`.

The implementation is ported to Python and shares Fraudline's FastAPI process.
It uses lexical retrieval and an explicit control-factor ranking channel, **not**
Proofline's gte-small embeddings, Supabase backend or OpenRouter generation.
The small local corpus and extractive answers keep the demo free and avoid
transmitting transaction details to a language-model provider. This is bounded
orchestration, not an autonomous LLM agent. Its three allowed steps cannot execute
financial actions, change a model probability or alter policies.

The original OWASP corpus concerns AI security, not banking fraud policy. No OWASP
passages were copied into this app. The new playbooks are original illustrative
guidance that an institution must replace and approve before operational use.

## MIT License — Proofline application code

Copyright (c) 2026 hafiz-fansuri

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
