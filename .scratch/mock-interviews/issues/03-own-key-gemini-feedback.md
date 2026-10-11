# 03: Give confirmed responses bounded Gemini feedback with the Learner's own key

**GitHub issue:** [#23](https://github.com/fahim36/ChickenKiller/issues/23)

**What to build:** A Learner explicitly enables their own free-project Gemini key and receives useful feedback on a confirmed response, while consent refusal, missing keys, quota exhaustion and failures preserve self-review.

**Blocked by:** 01 — Start a private Mock Interview with reviewed self-review.

**Status:** ready-for-agent (breakdown approved; blockers still gate implementation).

## Acceptance criteria

- [ ] Extend settings with explicit interview key use, Free Tier/billing-disabled confirmation and processing consent. Explain that confirmation is attestation rather than billing verification or a zero-billing guarantee, and that free-tier Google product-improvement processing is distinct from local retention.
- [ ] Use only the owner's enabled Gemini Developer API key through encrypted key handling. Do not inherit legacy Admin-key/CLI/provider fallbacks or accept unrelated/custom provider endpoints for interviews. Existing legacy grading behavior remains covered by regression checks.
- [ ] Recheck ownership, interview enablement, consent, eligible session state and available budget before each provider operation. Declining consent or lacking an enabled key keeps reviewed self-review available.
- [ ] Require explicit learner confirmation of the response text before feedback. Keep immutable evaluated text/version evidence so later correction does not rewrite what an assessment evaluated.
- [ ] Return short structured rubric-grounded feedback, exact response evidence, uncertainty, missing reasoning and relevant Lesson links. Validate evidence quotes and reviewed follow-up IDs; an invalid output becomes a retriable pending/error state, never a fabricated score or canonical prompt.
- [ ] Feedback selects at most one relevant reviewed follow-up in the same request. Turn progression is delivered in ticket 06; the returned reviewed selection is verifiable in this slice.
- [ ] Add shared operation accounting for at most 18 actual Gemini request attempts per session, including failures/manual retries, and one Gemini request in flight per learner across sessions. Reserve atomically, prevent duplicate spending and account for or disable SDK retries.
- [ ] On quota exhaustion, invalid keys, timeouts, malformed output and provider unavailability, preserve the confirmed response and offer self-review/manual retry where budget permits. Never automatically retry quota exhaustion, switch keys, bill through another provider or classify missing feedback as a poor answer.
- [ ] Use a currently verified free-tier-capable Gemini model and short structured context/output limits; do not send unrelated full histories or promise universal free quotas. No real provider calls in ordinary tests or CI.
- [ ] Demonstrate enable/consent -> confirmed response -> feedback -> saved result, with race/idempotency, ownership, quota, key-removal and legacy-grading regression tests.

## Scope

Typed/confirmed-text feedback is the usable slice. The same operation policy will cover audio requests later. No audio recording, free-form canonical prompt generation or speech generation.
