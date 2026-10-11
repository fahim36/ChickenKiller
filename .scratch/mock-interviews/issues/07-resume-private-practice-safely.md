# 07: Resume private practice and pending feedback within retention and quota limits

**GitHub issue:** [#27](https://github.com/fahim36/ChickenKiller/issues/27)

**What to build:** A Learner can leave, return to their private practice history, continue eligible unfinished work or retry pending feedback without duplicate requests, lost answers or recovery promises after audio expiry.

**Blocked by:** 04 — Record a voice response, confirm its transcript and receive feedback; 06 — Complete guided scenarios with a reviewed follow-up and practice retry.

**Status:** ready-for-agent (breakdown approved; blockers still gate implementation).

## Acceptance criteria

- [ ] Provide an owner-only session/history entry point showing progress, pending transcription/feedback, self-review and completed feedback. Reflect the same 30-day text lifetime, learner deletion and temporary-audio expiry already enforced by earlier slices.
- [ ] Resume a paused session using the reviewed prompt/rubric and turn evidence/version it originally used. Recheck ownership, Active Stack status, current key/consent and remaining budget before new work; content changes or Stack deactivation produce a clear safe state.
- [ ] A confirmed transcript can request pending feedback later without audio retranscription. Manual retries count as new provider attempts; duplicate clicks/refreshes/tab races do not create duplicate requests or reset the session cap.
- [ ] Untranscribed recordings are playable/retriable only until their actual 24-hour expiry. Once deleted/expired, show unavailable audio and offer eligible rerecording within the replacement/turn bounds or reviewed self-review, never fabricated recovery.
- [ ] Removing/replacing a key or withdrawing processing consent prevents new provider sends while leaving private self-review/history available. In-flight cancellation/deletion results cannot resurrect private content; retention cleanup and late jobs remain consistent.
- [ ] Distinguish quota exhaustion from transient/unavailable feedback without promising a universal reset time or free interview allowance. Do not create background quota retries or silently replenish an exhausted session request budget.
- [ ] Verify history -> resume -> manual retry -> saved feedback -> delete/expiry, including multiple tabs, cross-owner requests, deleted recordings, changed content, late jobs, consent withdrawal and key changes.

## Scope

Resume/history workflows build on already-working retention and privacy; do not postpone those safeguards to this ticket. No sharing, Admin access to responses or recurring automatic AI retries.
