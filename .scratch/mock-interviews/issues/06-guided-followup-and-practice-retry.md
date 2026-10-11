# 06: Complete guided scenarios with a reviewed follow-up and practice retry

**GitHub issue:** [#26](https://github.com/fahim36/ChickenKiller/issues/26)

**What to build:** A Learner can finish guided practice: explain the main scenario, handle one relevant reviewed follow-up, optionally improve the main answer and see evidence-based next practice suggestions.

**Blocked by:** 03 — Give confirmed responses bounded Gemini feedback with the Learner's own key.

**Status:** ready-for-agent (breakdown approved; blockers still gate implementation).

## Acceptance criteria

- [ ] A session has up to three distinct eligible Concepts, one main response per scenario, at most one 45-second follow-up and one optional 60-second practice retry of the main scenario. Reject duplicate/out-of-order/extra turns atomically rather than trusting disabled UI controls.
- [ ] Use only the reviewed follow-up selected by the already-bounded feedback response. Validate its membership/relevance; a follow-up cannot recursively create more follow-ups. No extra Gemini call merely selects a follow-up.
- [ ] Practice retries reuse the main scenario/rubric and may compare confirmed-response evidence with earlier feedback. Do not claim learning improvement merely from a repeated answer or produce accent/readiness scores.
- [ ] Typed confirmed responses work end to end independently of the audio tickets. When voice is installed, all turn kinds use the same recording/confirmation path and their respective limits; do not duplicate provider/budget policies.
- [ ] Learners can skip follow-ups/retries and finish without being marked wrong. Self-review mode uses reviewed options and rubrics without an AI request or a fake AI selection.
- [ ] Enforce the nine-evaluated-response bound and existing 18-request attempt budget. Retries/failures may exhaust budget sooner; stop AI requests truthfully and retain self-review, with no quota auto-retry or alternate key.
- [ ] Show concise session suggestions and teaching Lesson links, distinguishing reviewed self-review, pending feedback and completed AI feedback. Display uncertainty and evidence; preserve complete separate interview history.
- [ ] Verify session-state transitions, reviewed selection, evidence-based comparison, shorter sessions, maximum/duplicate turns and unchanged Quiz/Retake/Streak/Weak Concept behavior through rule/API/UI tests.

## Scope

No extra content batch, speech provider or AI-generated canonical questions. Voice and Whisper are useful but not genuine prerequisites for this typed, demoable guided-practice slice.
