# 01: Start a private Mock Interview with reviewed self-review

**GitHub issue:** [#21](https://github.com/fahim36/ChickenKiller/issues/21)

**What to build:** A Learner can start optional practice for studied topics, answer without AI, inspect a reviewed rubric, and keep or delete their private session. This is the first complete usable slice and the safe fallback for subsequent AI/voice work.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent (breakdown approved; blockers still gate implementation).

## Acceptance criteria

- [ ] Define reviewed Interview Prompt content separately from the Question Bank: stable identity, Stack, Concept, teaching Lesson, scenario, rubric, misconceptions, Sources and reviewed follow-up options. Validate and import it through the reviewed content pipeline; malformed or unresolved content cannot be published.
- [ ] Supply four reviewed seed prompts, one per existing Stack, included in the final 16 rather than an extra batch. Source research is current and primary; existing Questions, Syllabuses and released Challenges remain unchanged.
- [ ] A Learner can choose an Active Stack and eligible topics, start practice and submit an optional typed response or skip. Eligible Concepts come from Completed Lessons or already-played Daily Challenges, using consistent existing eligibility semantics.
- [ ] Recommend Weak Concepts among eligible reviewed prompts, then other eligible Concepts. A session uses up to three distinct Concepts; one or two qualifying Concepts produce a shorter session. With none, show a reason and useful Lesson link instead of unstudied scenarios.
- [ ] Show the reviewed self-review rubric and Lesson links without any provider call, key or AI-processing consent. A skipped response is not incorrect.
- [ ] Persist session and response evidence separately from quiz Answer correctness. Existing Quiz results, unlocking, Retakes, Streaks and Weak Concept calculations are unaffected.
- [ ] Retain owner-only text history for 30 days, with deletion and automated expiry cleanup working from this slice. Preserve the reviewed content/version used in historical sessions when content changes.
- [ ] Non-owners, including an Admin acting as another Learner, cannot read or alter private responses. Operational logs contain no response text or credentials.
- [ ] Demonstrate imported reviewed content -> eligible session -> response -> self-review -> private history -> deletion/expiry through meaningful content/API/UI tests. External providers are not needed.

## Scope

No AI, audio or deployment. Add the smallest session/content seams needed for this usable flow; do not create a standalone wide refactor or alter the legacy Grader contract.
