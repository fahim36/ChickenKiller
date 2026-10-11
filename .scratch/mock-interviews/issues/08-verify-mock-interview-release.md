# 08: Verify the complete free-quota Mock Interview release

**GitHub issue:** [#28](https://github.com/fahim36/ChickenKiller/issues/28)

**What to build:** The full guided practice experience is reviewable and release-ready across all four Stacks, with measured transcription decisions, trustworthy failure behavior and reproducible operation instructions.

**Blocked by:** 02 — Publish 16 reviewed Interview Prompts across the four Stacks; 05 — Benchmark Whisper and select a safe transcription path for voice practice; 07 — Resume private practice and pending feedback within retention and quota limits.

**Status:** ready-for-agent (breakdown approved; blockers still gate implementation).

## Acceptance criteria

- [ ] Verify the imported 16-prompt release across all four Stacks, studied-topic/Weak Concept selection, three/shorter/empty sessions and manual topic choice, with no existing Question/Syllabus/Challenge mutations.
- [ ] Exercise the complete learner path: own free-project confirmation/processing consent -> spoken response -> transcript correction -> feedback -> reviewed follow-up -> optional retry -> session suggestions -> private resume/delete.
- [ ] Cover mic denial, unsupported media, playback/voice unavailability, uploads, cancellation, missing/removed keys, consent refusal/withdrawal, quota/18-request exhaustion, provider malformed output/timeouts, worker overload/unavailability, duplicate tabs and expired/deleted audio. Ordinary CI uses deterministic provider mocks, not external websites or paid/provider inference.
- [ ] Confirm no Admin/CLI/provider fallback, no Gemini speech-generation requests, no hidden SDK retries and no learning-progress mutation. Demonstrate atomic request/turn limits and learner ownership at the API boundary.
- [ ] Publish measured Whisper gate results and the actual selected path. If unverified/unsuitable, explicitly leave Whisper disabled and verify Gemini/self-review fallback. Do not turn missing production resources into a false benchmark pass.
- [ ] Evaluate feedback on reviewed representative responses, including plausible mistakes, negation, incomplete reasoning and transcription corrections. Evidence quotes and selected follow-ups resolve correctly; document observed limitations rather than claiming a readiness percentage.
- [ ] Verify mobile/desktop recording and text fallback, keyboard/screen-reader controls, visible microphone state and understandable privacy/consent/retention copy. English with varied accents is launch scope; Bengali support is not claimed.
- [ ] Complete appropriate full API/frontend checks, content validation, schema/import/migration checks and standards/spec review. Fix findings and record evidence before marking release-ready.
- [ ] Provide installation/upgrade/disable guidance for audio transport, temporary storage cleanup, optional worker/model resource limits and key/consent/request policy, plus an implementation progress record and rollout checklist. Production merge/deployment remain separately authorized actions.

## Scope

Final end-to-end verification and operation readiness, not a place to defer core security/retention/ownership checks. No automatic deployment, external messaging, paid provider setup or additional interview modes.
