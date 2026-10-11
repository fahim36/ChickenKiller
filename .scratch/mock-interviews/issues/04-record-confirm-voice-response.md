# 04: Record a voice response, confirm its transcript and receive feedback

**GitHub issue:** [#24](https://github.com/fahim36/ChickenKiller/issues/24)

**What to build:** A Learner can answer by microphone, listen back, confirm or correct the transcript and receive the same reviewed self-review or Gemini feedback as a typed response.

**Blocked by:** 03 — Give confirmed responses bounded Gemini feedback with the Learner's own key.

**Status:** ready-for-agent (breakdown approved; blockers still gate implementation).

## Acceptance criteria

- [ ] Add clear tap-to-start/stop recording, microphone status, playback, skip and an optional typing fallback on supported desktop/mobile browsers. Device speech reads prompts/feedback with visible text; do not invoke Gemini speech generation, and gracefully handle unavailable voices/playback.
- [ ] Enforce main-answer 90-second, follow-up 45-second and practice-retry 60-second limits by turn kind. Permit at most one replacement recording per turn; reject stale/cross-session recordings and duplicate uploads.
- [ ] Provide bounded authenticated audio transport and temporary private storage compatible with supported browser recording formats. Validate type, decoded duration and byte limits server-side; respect or deliberately configure ingress limits without exposing the private API/key to the browser.
- [ ] Use the consented owner's Gemini recorded-audio transcription as the initial verifiable path. Every actual transcription attempt consumes the shared 18-request session budget and respects the per-learner in-flight guard.
- [ ] Show transcript confirmation/correction before any feedback request. Preserve evaluated text identity, avoid retranscribing a confirmed transcript on feedback retry and never grade raw unconfirmed recognition output.
- [ ] Refused microphone/Google consent, absent keys, upload failures, cancellation, timeouts and quota exhaustion leave a truthful state with typing or reviewed self-review/playback where available. Without a transcript, do not manufacture text or claim AI feedback is possible yet.
- [ ] Delete raw audio after transcript confirmation. Expire awaiting/failed-transcription audio after at most 24 hours; owner deletion and cancellation/abandonment cleanup remove relevant stored blobs. Display expiry and do not promise recovery after expiration.
- [ ] Private playback and downloads require owner authorization; no raw audio, response text or credentials leak to logs, Admin views or other Learners. Disclose that local deletion does not control Google's processing.
- [ ] Demonstrate record -> temporary playback -> Gemini transcript -> correction/confirmation -> audio deletion -> feedback/self-review. Mock providers in normal tests; verify supported recording formats, size/duration, retention and accessibility/error paths.

## Scope

This slice provides working voice practice before Whisper is available. Whisper selection remains gated by ticket 05; neither this ticket nor its tests promise unlimited free audio processing.
