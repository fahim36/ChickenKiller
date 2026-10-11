# 05: Benchmark Whisper and select a safe transcription path for voice practice

**GitHub issue:** [#25](https://github.com/fahim36/ChickenKiller/issues/25)

**What to build:** The working voice flow uses server-side faster-whisper when measured transcription quality and spare capacity justify it, and otherwise remains usable through the consented Gemini audio path.

**Blocked by:** 04 — Record a voice response, confirm its transcript and receive feedback.

**Status:** ready-for-agent (breakdown approved; blockers still gate implementation).

## Acceptance criteria

- [ ] Benchmark representative English recordings with varied accents, quiet/noisy conditions, technical terms and meaning-changing recognition errors. Record provenance/permission, expected transcripts, measured quality and limitations; do not substitute synthetic-only tests for unverified representative quality.
- [ ] Record candidate model/quantization, hardware, spare RAM/CPU, warm/cold latency, concurrency effects and the target of at most 20 seconds to transcribe a 90-second answer. Check existing app responsiveness under bounded load, not just an isolated third-party benchmark.
- [ ] Use an isolated/staging or explicitly authorized benchmark environment. Do not deploy a worker or load-test production merely because this ticket exists. If deployment hardware/corpus access is missing, report what is unverified and leave Whisper disabled.
- [ ] If suitable, integrate one resource-limited worker with a bounded queue into the existing owned recording -> transcript-confirmation flow. Whisper transcription consumes no Gemini request; feedback still uses the same consent/key/request policy.
- [ ] Keep the chosen approved Whisper path for ordinary corrections while available. If the gate fails, capacity/queue is unavailable or a bounded transcription fails, offer the Gemini audio fallback only with consent, an enabled own key and budget; otherwise retain temporary playback/self-review.
- [ ] Worker jobs honor ownership, cancellation, audio expiry/deletion and response revision; late results cannot resurrect deleted recordings or overwrite a confirmed transcript.
- [ ] Expose truthful selected-path/processing/error state in the learner flow and bounded operational diagnostics without private audio/text. Document worker installation, model storage, resource limits and rollback/disable behavior.
- [ ] Demonstrate record -> selected Whisper/Gemini path -> confirmed transcript -> feedback/self-review, plus tests for overload, expiry, duplicate jobs, unavailable worker and no hidden quota spending.
- [ ] Finish with a documented enable/disable decision. A failed or infeasible Whisper gate completes the ticket with Gemini audio as the selected path; it does not leave all other release work permanently blocked or claim an unrun benchmark passed.

## Scope

Benchmark plus conditional end-to-end integration, not a research-only dependency or mandatory new hosting purchase. Browser Whisper, GPU provisioning and paid transcription are outside scope.
