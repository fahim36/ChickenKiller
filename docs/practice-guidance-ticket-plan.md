# Proposed tickets: guidance from practice evidence

Status: concrete draft for breakdown review; not yet published to GitHub. Tracker: fahim36/InterviewCrackerAssistant. Proposed label: ready-for-agent. No parent issue is supplied and existing issues are not modified.

Each ticket is an end-to-end behavior with its own acceptance checks. No standalone prefactoring ticket is needed: the existing rule modules provide useful seams, and any narrowly necessary prefactoring belongs in its owning slice. Dependencies are completion blockers, not priorities.

## 1. Prevent retired Questions from blocking Lesson completion

**What to build:** A Learner never has to answer retired content to finish an already-passed Lesson Quiz, and can see why a pending Retake was replaced or waived.

**Blocked by:** None (can start immediately).

**Proposed status:** ready-for-agent

- [ ] Retirement of the original missed Question removes its pending Retake requirement with a recorded retirement reason.
- [ ] A retired waiting Retake is replaced with an active sibling; if none exists, waive only that requirement with a recorded content-gap reason, without falling back to the original Question.
- [ ] Retake retrieval and submission both enforce the rule, including retirement after a Question was displayed; repeated requests are safe.
- [ ] A Lesson completes only if its Quiz passed and every other Retake is resolved; waivers generate no correct Answer evidence.
- [ ] Show replacement/waiver reasons in the learning flow; preserve Completed Lessons and finished Challenge scores.
- [ ] API, rule and UI checks cover original retirement, waiting-sibling retirement, no sibling, concurrent/repeated requests and failed-Quiz protection. Follow ADR-0009.

## 2. Show Weak Concept evidence on each Stack page

**What to build:** A Learner can inspect each active Stack's Concept evidence, identify recent weaknesses and recovery, and open the relevant Lesson.

**Blocked by:** None (can start immediately).

**Proposed status:** ready-for-agent

- [ ] Trigger weakness after incorrect answered outcomes on two distinct active Questions in the current and preceding 29 UTC Days; repeated misses on one Question do not inflate the count.
- [ ] Recovery requires correct recorded answers strictly after the latest qualifying miss on three distinct UTC Days across at least two distinct active Questions; a new miss restarts recovery.
- [ ] Use actually answered recorded Lesson Quiz, Challenge, Retake and Review outcomes; exclude unanswered slots, ungraded results, replays and retired Questions.
- [ ] Rank weak Concepts by distinct recent missed Questions, then latest qualifying miss and stable Concept ID; show supporting counts/dates rather than mastery percentages.
- [ ] Distinguish insufficient evidence, expiration and recovery; deactivation hides guidance without losing history and reactivation recalculates current evidence.
- [ ] Serve only the signed-in Learner's evidence and provide accessible Stack-page evidence and Lesson links, including missing/removed Lesson handling.
- [ ] Fake-clock rule tests and API/UI checks cover UTC/window boundaries, repeated attempts, recovery resets, retirement and cross-Learner/Stack isolation.

## 3. Recommend one useful Next Action on Home

**What to build:** After a Daily Challenge, a Learner sees one optional, actionable recommendation and up to three Weak Concepts across Active Stacks.

**Blocked by:** 1. Prevent retired Questions from blocking Lesson completion; 2. Show Weak Concept evidence on each Stack page.

**Proposed status:** ready-for-agent

- [ ] Choose oldest pending Retake first, then eligible due Review for the highest-ranked Weak Concept, then an Unlocked Lesson in the most recently practised Stack.
- [ ] If no Lessons remain, offer ordinary due Review; with no eligible activity, show completion and links to Materials/Milestones.
- [ ] Break remaining ties deterministically; Stacks with no recorded practice use stable ordering.
- [ ] A weak-Concept Review action opens practice for that Concept drawn only from the existing due queue, and submissions retain normal eligibility checks; do not expose a new non-due practice bypass.
- [ ] Show a reason, evidence and working links; preserve other activities, shared Daily Challenges, Streak rules and optional Review.
- [ ] Handle retirement-safe pending Retakes and sparse/empty evidence without dead recommendations.
- [ ] API/UI and integrated checks demonstrate ordering, tie handling, targeted due Review, fully completed Stacks and empty queues.

## 4. Let Learners submit and track private Question Reports

**What to build:** After answering an active Question, a Learner can report a defect, edit an Open report and inspect their own report status.

**Blocked by:** None (can start immediately).

**Proposed status:** ready-for-agent

- [ ] Support one required category: wrong answer, ambiguous wording, outdated claim or broken Source, plus an optional note.
- [ ] Expose reporting from answered Lesson Quiz, Challenge, Retake and Review views; verify report eligibility on the server and show retirement reasons instead of inviting reports on retired Questions.
- [ ] Persist at most one unresolved report per Learner and Question, including concurrent submissions; only Open reports are editable.
- [ ] Provide an accessible submission/editing flow and a private view of the reporter's own reports and statuses.
- [ ] Enforce reporter/Admin access in reads and mutations; guessed identifiers cannot reveal another Learner's report.
- [ ] Filing or editing reports changes no score, Streak, Missed Question or completion; this does not implement legacy Disputes.
- [ ] API/UI tests cover categories, validation, concurrent deduplication, after-answer eligibility, retirement and authorization.

## 5. Let Admins review Question Reports grouped by Question

**What to build:** An Admin can inspect corroborating reports, accept a defect awaiting publication or close a report with an explanation, and the reporter sees the decision.

**Blocked by:** 4. Let Learners submit and track private Question Reports.

**Proposed status:** ready-for-agent

- [ ] Group private reports by Question in an Admin-only queue while keeping other reporters hidden from each Learner.
- [ ] Allow Open reports to become Accepted, awaiting publication, or Closed for declined/duplicate reports; require an Admin explanation.
- [ ] Reporter status views display the decision and explanation, and accepted reports can no longer be edited.
- [ ] Accepting a report neither publishes content nor marks it Resolved; route corrections through the existing reviewed immutable-content pipeline.
- [ ] Transitions are validated and repeated/concurrent decisions cannot silently overwrite an already decided report.
- [ ] API/UI checks demonstrate grouped review, explanation validation, privacy, transition protection and unchanged learning results.

## 6. Resolve accepted Question Reports when their correction is imported

**What to build:** A reporter sees Resolved only after the correction associated with their accepted Question Report has reached the imported app content.

**Blocked by:** 5. Let Admins review Question Reports grouped by Question.

**Proposed status:** ready-for-agent

- [ ] Associate an accepted report with its expected retirement/replacement outcome using permanent Question IDs, and make the association reviewable by the Admin.
- [ ] After import confirms that exact outcome, mark the associated accepted report Resolved and expose the resolution in reporter/Admin views.
- [ ] An unrelated import, an unimported content draft, failed import or Admin acceptance alone cannot resolve a report.
- [ ] Repeated imports/transitions are idempotent; correction verification and resolution cannot claim success before the relevant import commits.
- [ ] Keep the existing reviewed content pipeline and immutable-Question rules; preserve recorded scores and report privacy.
- [ ] Import/API/UI checks cover correct and unrelated imports, missing replacement, transaction failure, retries and in-app status updates.

## 7. Add varied Questions to a bounded set of thin Concepts

**What to build:** Learners get additional sourced scenario variants through existing Lesson Quizzes, Retakes and Review for a small, auditable content batch.

**Blocked by:** None (can start immediately).

**Proposed status:** ready-for-agent

- [ ] Choose two thin Concepts per committed Stack by fewest active Questions, with stable Concept ID ties; record the selected eight Concepts and existing coverage.
- [ ] Bring each selected Concept to at least four active Questions using new permanent IDs; if coverage has already improved, choose the next thin Concept.
- [ ] Across each selected Concept's variants, test materially different applications such as tracing, debugging or changed constraints rather than paraphrasing.
- [ ] New Questions are multiple choice or Multiple select, preserve the applicable quiz mix, and contain accurate Explanations and Sources fetched during the research run.
- [ ] Add and import through the existing reviewed content flow; never edit/delete existing Questions or released Challenges.
- [ ] Existing schema/content checks pass, and demonstrate that the added variants are available through ordinary Lesson Quiz, Retake or eligible Review flows.
- [ ] This is an initial content batch, not a requirement to enrich every Concept or a blocker for the other feature implementations.

## 8. Measure delayed variant performance after targeted practice

**What to build:** An Admin can inspect whether Learners answer distinct, previously unrecorded variants correctly 7–14 Days after targeted practice, with denominators and limitations.

**Blocked by:** 3. Recommend one useful Next Action on Home.

**Proposed status:** ready-for-agent

- [ ] Record recommendation uptake and the Concept actually practised through the targeted Review action; a click alone is not completed practice.
- [ ] Attribute a later answer to the most recent completed targeted practice of the same Learner/Stack/Concept that precedes it; include it only when that practice is 7–14 UTC Days earlier.
- [ ] Count each qualifying Question once per Learner/Stack using its first recorded, actually answered, graded outcome; exclude retired Questions, repeats and waiver events.
- [ ] Expose an Admin-only summary of accuracy, qualifying answers, Learners and Concepts plus recommendation uptake and Retake completion; show an honest empty state.
- [ ] State that unrecorded replays mean first recorded answer is not proven first exposure; avoid mastery or interview-readiness claims.
- [ ] Show the descriptive measure with denominators rather than implying causality or a validated optimal delay; do not log keys or answer text in general analytics.
- [ ] Fake-clock/API/UI checks cover Day 7/14 boundaries, multiple practice sessions, wrong-Concept attribution, repeated answers, retirement, privacy and sparse samples.

## Dependency graph and release scope

Startable tickets: 1, 2, 4 and 7. Ticket 3 follows 1 and 2; ticket 5 follows 4; ticket 6 follows 5; ticket 8 follows 3. Content enrichment (7) improves quality but is not a software dependency. The release is complete when all eight slices and their relevant existing checks pass; publication/deployment is a separate action.

The specification has been accepted as the basis for ticket planning. This draft adds concrete implementation defaults for the bounded content sample and metric attribution; they are visible here for approval with the breakdown. Ticket publication waits for the approval required by the to-tickets skill. After approval, create issues in dependency order, use real issue identifiers in the bodies and native GitHub blocking relationships where available, and verify the resulting issues and edges.

