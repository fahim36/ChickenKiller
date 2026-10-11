# Practice outcomes: interpretation and recording

Admins open **Settings → Practice outcomes**. `/admin/practice-outcomes` is Admin-only and returns aggregates, never learner identities, answer text or API keys.

## What is recorded

- A targeted Review page with a due queue sends an authenticated POST to `/review/uptake`. A visit is counted once per Learner/Stack/Concept/UTC Day. Reloads are deduplicated. This is an uptake proxy, with no recommendation-impression denominator; manually opening a targeted URL can count too. An unavailable or empty queue does not count. Instrumentation failures leave practice available.
- A targeted Review submission includes `target_concept_id`. The server verifies it against the active Question and existing Review eligibility under the Learner/Stack lock. A nonblank, successfully graded recorded answer creates a targeted-practice event in the same transaction. Wrong answers count as practice; skipped/unanswered Questions and failed grading do not. Each answered Question is an event, rather than claiming an entire Review session was finished.
- Events are recorded from this release onward. Earlier targeted practice cannot be reconstructed from ordinary Answer history. No historical practice events are backfilled.

## Delayed performance

The summary reads recorded history up to the server clock. For each Learner/Stack/Question, it considers only the earliest recorded Answer, ordered by time and then Answer ID. If that first record is unanswered, ungraded or a Retake, a later answer cannot make the Question a fresh recorded variant. Currently retired Questions are excluded without changing stored scores.

For an eligible first answer, use the most recent completed targeted-practice event for the same Learner, Stack and Concept **strictly before** the answer timestamp. A practice event cannot attribute its own answer to itself. Compare UTC calendar dates, including differences of **7 and 14 Days**. A more recent practice event outside this window overrides an older eligible event.

Accuracy is correct qualifying answers divided by all qualifying answers. With no qualifying answers it is null, never 0%. Learner counts are distinct people; Concept counts are distinct Stack/Concept pairs. Small samples remain visible alongside their denominators.

Supporting totals show uptake days and participating Learners, completed targeted-practice answers and participating Learners, and correctly completed Retakes out of recorded Retakes. Content waivers are separate from correct Retake completion. These totals cover recorded history, not a conversion funnel or a causal comparison.

Challenge replays are unrecorded, so first recorded answers do not prove first exposure. This is a descriptive measure, not a mastery or interview-readiness estimate. The 7–14 Day window is an evaluation choice, not a validated optimal delay. No control group or causal benefit is claimed.
