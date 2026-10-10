# Next release: guidance from practice evidence

Status: agreed design, advanced to ticket planning by the request to use to-tickets. The proposed breakdown awaits review; implementation has not started.

## Audience, outcome and scope

Serve experienced developers preparing for an interview soon. The primary outcome is better performance on distinct variants after a delay. Return visits and Streaks are supporting signals, not evidence of understanding.

The release contains Weak Concepts, one Next Action, private Question Reports, and the retirement handling required to make those features coherent. Enrich important Question variants alongside development. Placement Quizzes follow once diagnostic coverage is sufficient. No delivery date or hours budget has been agreed.

The existing shared Daily Challenge, first-answer scoring, UTC Days, optional Review, Pass Mark and completion-based Lesson path remain the foundation. Terminology is in [CONTEXT.md](../CONTEXT.md); the consequential retirement decision is in [ADR-0009](adr/0009-retirement-removes-pending-retake-blockers.md).

## Weak Concepts

Calculate evidence per Learner and Stack from recorded, actually answered Lesson Quiz, Daily Challenge, Retake and Review answers. Exclude unanswered slots, ungraded outcomes, unrecorded replays and retired Questions. Existing Question-level Missed Question rules remain unchanged.

A Concept becomes weak after incorrect answers to at least two distinct active Questions within 30 UTC Days. Multiple misses on one Question contribute one distinct Question, though the most recent qualifying miss restarts recovery. Correct answers strictly after that latest miss clear the signal when they cover at least two distinct active Questions across at least three different UTC Days. Multiple correct answers on one Day contribute one Day. Repeated answers are recovery evidence, not proof of unfamiliar-Question competence.

Use a rolling window of the current UTC Day and the preceding 29 UTC Days for the initial trigger. Recalculate using active Questions after retirement. Expired evidence must not be presented as recovery. Show evidence counts and dates rather than a mastery percentage. Sparse evidence is labelled “Not enough evidence”; expired evidence can be labelled “No recent evidence.” A cleared signal describes recovery under this rule and does not certify interview readiness.

Rank Weak Concepts by the number of distinct recently missed active Questions, then by most recent qualifying miss. Use a stable Concept ID order for any remaining tie. Deactivating a Stack hides its guidance without deleting history; reactivation uses evidence still within the applicable window.

These thresholds are adjustable initial product rules, not scientifically validated mastery thresholds. Adjustments should be documented and evaluated; they do not alter historical scores or completed progress.

## Home and Stack pages

Home displays one Next Action and up to three Weak Concepts across Active Stacks, with evidence and links to their teaching Lessons. Each Stack page provides its fuller Concept evidence list. The recommendation explains its reason and remains optional; other activities stay accessible.

Next Action ordering:

1. The oldest pending Retake, after resolving any retirement blocker.
2. Due Review for a Weak Concept, using the Concept ranking above.
3. The Unlocked Lesson in the most recently practised Active Stack.
4. If no Lessons remain, ordinary due Review.
5. If no eligible activity remains, show completion with links to Materials and Milestones.

Use stable identifiers to break remaining ties. For a Stack with no recorded practice, use a stable Stack order as fallback. Do not create a new unrestricted practice mode in this release. Existing Review due-queue eligibility remains authoritative; a Question tagged to a Locked Lesson can be eligible through an existing miss or a played Challenge. A Weak Concept without eligible Review must not produce a practice button that the API will reject.

The Daily Challenge continues to be displayed through the current Home flow. This Next Action sequence guides additional learning; it does not redefine Streaks or require Review before another activity.

## Question Reports

After answering, a Learner can report an active Question using one required category: wrong answer, ambiguous wording, outdated claim or broken Source. An optional note provides supporting detail. A retired Question shows its retirement reason instead of inviting another report.

There is at most one unresolved report per Learner and Question. Open reports are editable; accepted reports await the Admin/content process. Admins can group reports about a Question without exposing other reporters to Learners.

Reports and status are private to the reporter and Admin. A Question Report is distinct from the glossary's Dispute about legacy written-answer grading; a Dispute workflow is outside this release.

Lifecycle:

- **Open:** awaiting Admin review.
- **Accepted, awaiting publication:** Admin accepts the defect with an explanation; the content change has not yet been imported.
- **Resolved:** the relevant retirement/replacement has been imported.
- **Closed:** declined or duplicate, with an Admin explanation.

Admin acceptance does not automatically publish changes. Continue using the existing reviewed, immutable content pipeline. Verify resolution against the imported correction for that Question rather than any unrelated content import. Status updates appear in the app; email/push delivery is outside the release.

Filing or accepting a report does not change recorded scores. Other Learners see confirmed retirement explanations through the existing content flow rather than unresolved private reports.

## Retirement and pending Retakes

Retired Questions are excluded from future practice and Weak Concept evidence. Preserve recorded scores and display the retirement explanation. Never undo a Completed Lesson.

- If the original missed Question is retired, remove its pending Retake requirement with a retirement reason.
- If the waiting Retake Question is retired while its original missed Question is still active, replace it with an active sibling on that Concept.
- If no active sibling can replace it, waive that pending requirement with a recorded content-gap reason. Do not ask the retired waiting Question or silently reuse the original Question.

Only a Lesson Quiz that already met its Pass Mark can complete through these resolved/waived requirements. Waiving a Retake does not award quiz points. Other pending Retakes still need resolution. New waiver outcomes must be distinguishable from successfully answered Retakes in stored evidence and Learner-facing explanations.

## Evaluation

Measure correctness on distinct variants with no prior recorded answer, attempted 7–14 UTC Days after targeted practice of the same Concept. Record which Concept the targeted practice addressed so the comparison is interpretable. Report the number of participating Learners, qualifying answers and Concepts; do not publish a meaningful-looking percentage without its denominator.

Challenge replays are unrecorded, so first recorded answers are a proxy for fresh variants, not proof of first exposure. Show that limitation. Retake performance and answers to already recorded Questions do not substitute for the primary measure. Instrument recommendation uptake and Retake completion as supporting outcomes, without logging API keys or answer text in general analytics.

Observe whether this flow is useful before claiming it improves learning. Where usage supports it, compare with a baseline/control; otherwise report descriptive results and usability findings with their limits. The initial 7–14 Day window is an evaluation choice, not an established optimal learning interval.

## Acceptance checks

### Weak Concept evidence

- Two incorrect answers to the same Question do not satisfy the distinct-Question trigger; incorrect answers to two different active Questions within the window do.
- Three correct answers on one Day do not clear a signal. Correct answers on three UTC Days across two active Questions after the latest miss do; a newer qualifying miss restarts recovery.
- Correct recovery before the latest miss is ignored. UTC midnight and the 30-Day window boundaries are deterministic under a fake clock.
- Unanswered, ungraded, replay and retired-Question evidence cannot trigger weakness or recovery.
- Expiration does not display improvement. Deactivation/reactivation preserves history and recalculates current guidance.
- Sparse banks produce an honest evidence state and no mastery claim.

### Recommendations

- Retakes outrank weak-Concept Review; weak-Concept Review outranks an Unlocked Lesson. Ties are stable and follow the documented ordering.
- Recommended Review Questions are accepted by the existing due-queue eligibility rules; non-due Questions are not exposed through a new bypass.
- Fully completed Stacks and empty queues have useful, nonblocking states. Guidance never changes Streaks or locks.
- Home and Stack views expose accessible evidence, reasons and working Lesson/activity links.

### Reports and authorization

- Only the reporter and Admin can read a report and its status. Another Learner cannot read or edit it by guessing an identifier.
- Concurrent duplicate submissions do not create multiple unresolved reports for the same Learner and Question.
- Only Open reports are editable by the reporter; Admin decisions require an explanation.
- A report cannot become Resolved because of an unrelated import. Acceptance alone never publishes content or changes scores.
- Reporting is available after answering an active Question; retired Questions display their reason.

### Retirement

- A retired waiting Retake is never presented as answerable. An active sibling replaces it when available.
- Retired originals and missing active siblings remove only the relevant pending requirement, with a visible reason.
- A failed Lesson Quiz never becomes passed through a waiver. Other pending Retakes remain required; Completed Lessons and finished Challenge scores remain recorded.
- Waived requirements do not generate correct Answer evidence or inflate recovery/evaluation measures.

### Measurement and content

- Primary measurement enforces the documented delay, Concept match and absence of prior recorded answers; denominators and replay limitations are shown.
- Relevant Question banks receive reviewed variants where coverage is insufficient. Existing immutable-content/schema checks remain applicable.
- Appropriate API, rule and UI tests cover these behaviors, including concurrent report creation and authorization. Existing relevant checks must pass before release; this document does not claim they have been run.

## Completion of the design interview

The decision frontier is closed. The request to use to-tickets advances this agreed specification to ticket planning. The proposed breakdown is in [practice-guidance-ticket-plan.md](practice-guidance-ticket-plan.md), awaiting the review required by that skill before publishing GitHub issues. Further implementation work requires an instruction to implement; ticket approval does not by itself authorize deployment.
