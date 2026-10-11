# Placement Quiz design interview

Design confirmed on 12 October 2026. User authorized sequential implementation after ticket generation, local-instance testing, and per-ticket commits and pushes on a feature branch, with continuation after natural usage-limit resets. Ticket breakdown awaits review before publication.

## Settled decisions

- Placement is an optional way to complete a Week's Lessons by demonstrating knowledge, rather than only a recommendation about where to start.
- The Pass Mark remains 80%. Question coverage must support completing the whole Week.
- New and existing Learners can use placement.
- Passing does not tick Milestones; hands-on completion remains a separate learner assertion.
- Placement targets only the earliest incomplete Week. Passing can make the next Week eligible.
- Pending Retakes belonging to the target Week must be cleared before placement starts. Existing Lesson completions are preserved.
- One submitted Placement Quiz attempt is allowed per Week. Failure directs the Learner to the normal Lesson path; an unsubmitted attempt can resume.
- Each eligible Week needs a reviewed placement coverage plan covering every Lesson and its essential Concepts, backed by sufficient suitable Questions.
- Passing requires at least 80% overall and at least 80% within every Lesson.
- A passing placement completes the Week's Lessons immediately. Placement misses enter optional Review and create no compulsory Retakes.
- Use five Questions per Lesson as the minimum (20 or 25 per current Week); use ten for a Lesson when its essential coverage requires more. Placement is unavailable when the reviewed coverage plan cannot be met.
- Only Questions the Learner has never seen can count. Insufficient fresh coverage makes placement unavailable and directs the Learner to the normal Lesson path.
- Correctness, Explanations and Sources appear only after final submission. Answers can change before submission; unanswered Questions count as incorrect.
- Failed-placement misses also enter optional Review. Failure completes no additional Lessons and preserves existing completions; results show each Lesson's score.
- Partially completed Weeks are still tested in full, including already completed Lessons.
- Allow one submitted attempt per Week teaching revision. Changes to its Lessons or essential coverage permit another attempt; Question additions or link fixes alone do not.
- Cancel unfinished attempts when the teaching revision changes or a drawn Question is retired. Explain why, consume no submission allowance, and permit a fresh attempt if fresh coverage exists. Already viewed Questions remain seen.
- No timer or automatic expiry. Save answers automatically and resume the same Questions and answers while content remains valid. Describe placement as a self-assessment and ask Learners to answer without outside help.
- Label progress as Completed by placement and link to the attempt. Keep placement evidence separate from Daily Challenge scores and Streaks.
- Updated Lessons preserve existing completion and do not reopen a completed Week for placement. New-revision attempt allowances apply only to incomplete Weeks.
- While placement is unfinished, block new Lesson Quizzes and Retakes in the target Week; study, Daily Challenges and Review remain available. Explicit abandonment consumes no submitted attempt, but viewed Questions remain seen.
- Pilot one reviewed Week per Stack. Entry belongs on the Week page with explanations for unavailable states; Admins receive a coverage view. Expand after verifying selection, scoring, completion, resume and content-change handling.
- A Question becomes seen when its prompt and options are first delivered to the Learner. Reserve drawn Questions for unfinished placement so other practice cannot expose them; resume retains reservations, while cancellation or abandonment releases them without erasing exposure history.
- Use reviewed multiple-choice and multiple-select Questions only, equally weighted. Multiple select uses exact-match scoring without partial credit. Display correct/total counts and require 80% overall and within every Lesson.
- Pilot Week 1 of each Stack. Admins review essential Concepts drawn from every Lesson's learning objectives; each essential Concept must map to a Question in the attempt. Add reviewed variants as needed and keep placement unavailable until coverage is sufficient.

## Open decisions

None. Design confirmed; ticket breakdown review is the next workflow step.

## Implementation acceptance boundaries

- Eligibility follows the earliest incomplete Week, permits new and existing Learners, preserves completed Lessons, and rejects pending Retakes in the target Week.
- The selector meets the reviewed coverage plan, five-or-ten Questions per Lesson, freshness and reservation requirements, or explains unavailability without drawing an invalid quiz.
- Exposure tracking must cover other practice surfaces. Historical answered Questions count as seen; historical unrecorded exposure cannot be reconstructed reliably and must not be claimed as known.
- Submitted attempts are immutable. Duplicate submission, concurrent tabs, abandonment, resume and teaching changes must not consume extra attempts or incorrectly complete Lessons.
- Submission rechecks content validity and eligibility. Completion and attempt consumption occur together; teaching revision changes or retirement cancel unfinished attempts instead.
- Placement misses from passing and failing submissions enter optional Review without compulsory Retakes; Daily Challenge scoring and Streaks stay separate.
- Week-wide completion preserves existing completion records, identifies newly completed Lessons as Completed by placement, and unlocks the next sequential work without ticking Milestones.
- Verify unavailable coverage, per-Lesson failures despite overall passing scores, unanswered items, exact-match scoring, reservations across practice, stale attempts, resume, abandonment and owner-only evidence.
- Pilot content must pass existing reviewed-content checks; physical UI verification covers the Week entry, explanations, saved answers and result-to-progress flow.

## Repository findings

Current source Weeks contain four Lessons, or five in the Agentic AI Engineer Stack, and 14–26 tagged Concepts. A six-Question quiz cannot cover all Concepts. Existing unlocking follows Completed Lessons rather than a separate Week gate. Existing quiz attempts pin their Syllabus version and drawn Questions; completion records currently lack a completion method. These findings describe source/code, not production coverage.

## Known terminology conflict

Completed Lesson now includes passing Placement Quiz completion. Placement has no compulsory Retakes; its missed Questions enter optional Review.
