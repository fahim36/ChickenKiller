# ChickenKiller feature opportunities

Analysis date: 10 October 2026.

## Recommendation and scope

Keep the shared Daily Challenge as the habit. Add a personal preparation loop around it: understand the Learner's goal, identify weak Concepts, recommend useful practice, and show evidence of improvement. Then add interview practice that tests explanation and application.

Positioning hypothesis: **A short daily interview-prep habit that turns mistakes into a personal preparation plan.** Validate this with Learners before treating it as a market conclusion.

This analysis covers repository documentation, web components/pages, API routes and rules, committed content, and official competitor sources. It does not include production analytics, user interviews, or a live authenticated UI audit. Committed content is not proof of production publication. Older status documents contain superseded deployment and grading information; implementation and newer ADRs take precedence.

## Existing foundation

Implemented capabilities include multiple Active Stacks with preserved progress; shared three-Question Daily Challenges; first-answer scoring; Streaks; copied Result Cards; Archive and Catch-up; graph/list Week maps; Lesson Materials and exercises; six-Question Lesson Quizzes; sibling Retakes; optional Review; self-ticked Milestones; versioned Syllabuses; immutable sourced Questions and retirement; Stack Requests; and MCP content drafts with Admin decisions.

Review already prioritizes Missed Questions and requires three correct UTC Days to clear a miss. Ordinary repeats use a fixed three-Day interval. Sources and Explanations already exist. These are foundations to improve, not missing features to reinvent.

Weak Concepts and Placement Quizzes are defined in [CONTEXT.md](../CONTEXT.md) and the older roadmap but were not found implemented in the inspected API/web routes. Stack Requests and open sign-up support already exist; older plans are not a reliable current feature inventory.

| Committed Stack | Lessons | Active Questions | Stack-local Concepts | Concepts with at most two active Questions |
| --- | ---: | ---: | ---: | ---: |
| Agentic AI Engineer | 80 | 1,100 | 468 | 318 |
| Android Developer | 48 | 600 | 290 | 273 |
| Full Stack Web Dev | 48 | 480 | 192 | 96 |
| Full Stack .NET Developer | 48 | 600 | 296 | 289 |
| Total | 224 | 2,780 | 1,246 | 976 |

Counts use the latest committed Syllabus per Stack and nonretired Questions in `content/*/question-bank/*.json`. Concepts are counted separately per Stack. All current Lessons have at least one tagged Question; that does not establish sufficient coverage or quality. No written Questions are active in this snapshot, although legacy code/content remains.

## Prioritized additions

Effort is relative: Small extends existing UI/models; Medium adds a bounded persisted workflow; Large adds substantial infrastructure/content/operations. These are scope estimates, not delivery promises. Priority assumes a small operating team and should change when usage evidence warrants it.

| Priority | Feature | Learner benefit | Effort |
| --- | --- | --- | --- |
| 1 | Weak Concepts and a recommended next action | Know what to improve and act immediately | Medium |
| 2 | Placement Quizzes | Skip familiar introductory Lessons | Medium |
| 3 | Richer variants and content health | Practise transferable knowledge, with more trustworthy feedback | Medium, ongoing |
| 4 | Interview goal and personal plan | Prepare within available time and a target date | Medium |
| 5 | Question reporting and Admin triage | Resolve ambiguity, wrong answers and obsolete claims | Small–Medium |
| 6 | Optional reminders and local reset display | Maintain the daily habit | Small–Medium |
| 7 | Explain-first mock practice | Practise reasoning and communication | Medium initially; Large with voice/AI |
| 8 | Practical Milestone evidence | Build work that can be demonstrated | Medium |
| 9 | Job-description skill mapping | Focus on a specific opportunity | Medium |
| 10 | Adaptive Review intervals | Reduce repetitive work while retaining weak Concepts | Medium |
| 11 | Search, bookmarks and mistake notes | Retrieve useful past material | Small–Medium |
| 12 | Private practice groups and richer sharing | Add accountability and test referrals | Medium |

### 1. Weak Concepts and next actions

Show three to five Concepts needing attention, recent evidence, the teaching Lesson, and a practice button. Example: “Coroutine cancellation: missed two of three distinct Questions recently. Review the Lesson, then try a new scenario.” Separate untested Concepts from weak ones and identify sparse evidence. Use recent distinct-Question results rather than lifetime miss totals, which penalize frequent practice. Distinguish first attempts from repeated answers.

Start with transparent rules. After the Daily Challenge, recommend one action: resume pending Retakes, practise a weak Concept, or continue the Unlocked Lesson. Respect locking rules and keep Review optional. Track whether recommendations are used and whether fresh-variant performance improves after a delay.

Implementation footholds: [models.py](../api/app/models.py) relates Answers, Questions, Concepts and Lessons; [reviews.py](../api/app/reviews.py) gathers practice history; [home page](../web/src/app/page.tsx) provides the entry point. Avoid recalculating full-Stack analytics on every Question submission.

### 2. Placement Quizzes

Offer an optional diagnostic for the next eligible Week, sampling its Lessons and Concepts. Passing completes the Week under the documented Placement rule; failing recommends study and preserves existing progress. One six-Question sample should not imply competence across a whole Week. Establish a coverage blueprint and enough fresh Questions first.

Store placement evidence separately. Define interactions with pending Retakes, Syllabus versions, Updated Lessons and existing completions. Start with the next Week in the sequential path. Use later fresh-Question performance to check whether placement skipped too much.

### 3. Variants and content health

About 78% of Concepts have at most two active Questions. A missed Question can therefore leave only one sibling for repeated Retakes. Enrich variation before making strong mastery claims.

For important or frequently missed Concepts, add recognition, output tracing, debugging, tradeoff and changed-constraint variants. Prioritize gaps rather than an arbitrary count for every Concept. Keep Questions immutable: add new IDs and retire flawed originals.

Expand existing Admin coverage into content health: sibling counts, quiz composition, source age, link failures, pending reports and Lesson coverage. Reuse current content checks and Upcoming Challenge warnings. Link health and factual claim revalidation are separate tasks; a working link does not establish that a claim is current.

### 4. Goal-based preparation

Collect an optional role, interview date and weekly time budget. Plan due Review, prerequisite Lessons and practical Milestones; recalculate after missed study time or a changed goal. Explain priorities and show estimated workload.

Committed Lesson estimates alone total 72–80 hours per Stack, excluding Milestones and additional practice. Short deadlines need focused coverage and honest limits, not a promise to finish everything. Keep Daily Challenges shared; personalize the plan and optional practice.

### 5. Content reports

Add “Report this Question” after answering, with categories for wrong answer, ambiguity, outdated claim and broken Source. Deduplicate reports, show status and notify the reporter when resolved. Admin decisions retire/replace Questions through the existing content pipeline. Factual content reports are distinct from legacy grading disputes.

### 6. Reminders and timing

Show the local release time and a reset countdown. Keep UTC scoring: 00:00 UTC is 06:00 in Dhaka. Add one opt-in reminder channel, local scheduling, suppression after completion, delivery deduplication and unsubscribe controls. PWA installation can follow. Offline scored Challenges need additional synchronization, answer exposure and first-attempt decisions.

### 7. Explain-first practice

Begin with a curated 10–15 minute session: explain a Concept, solve a changed scenario, answer a follow-up, inspect a rubric, and receive two specific practice suggestions. Start with self-review. Later optional AI text/voice coaching should cite evidence from the response and acknowledge uncertainty.

Keep coaching separate from Daily Challenge scores and Lesson unlocking. [ADR-0008](adr/0008-multiple-select-replaces-written-questions.md) removed new LLM-graded Questions because of cost, latency and failure; a mandatory AI judge would undo that benefit. New practice formats need their own content schema and reviewed publication path.

### 8. Milestone evidence

Add optional repository/demo links, reflections and an interview explanation prompt to self-ticked Milestones. Distinguish “Learner marked complete” from “reviewed” or “tests passed.” A private portfolio view can organize evidence by Stack; sharing should be explicit.

Start with links and checklists. A later execution feature should support one language and a small exercise set first. Running arbitrary code requires isolation, memory/time limits and network restrictions; a full coding judge is a Large operational feature.

### 9–12. Useful extensions

- Job-description mapping: extract skills from a pasted description, let the Learner correct the mapping, link to existing Lessons and label unsupported skills as gaps. Do not auto-publish generated content or imply verified company interview frequency.
- Adaptive Review: extend intervals after successful delayed answers, shorten after misses, add short sessions and optional Stack filters. Confidence can be an additional signal. Validate simple schedules first; preserve three-Day miss clearance unless deliberately revising that product rule.
- Search and notes: search Lessons/Materials and already answered Questions. Respect locked quiz and unreleased Challenge boundaries. Attach notes to existing mistake history.
- Private groups: test friend invite links and a small weekly goal before building matching/scheduling. Richer Result Cards can provide spoiler-free previews and links to the same Challenge. Measure resulting activation, not just shares.

## Competitive implications and deferrals

[LeetCode](https://leetcode.com/studyplan/top-interview-150/) already provides curated plans. [HackerRank](https://www.hackerrank.com/mock-interviews) advertises several mock formats. [Aced/Exponent](https://www.tryexponent.com/practice?src=homepage) offers peer practice and [interviewing.io](https://interviewing.io/) offers interview simulations and feedback. These official descriptions establish categories, not product effectiveness or demand for ChickenKiller. Details are in [feature-research-sources.md](feature-research-sources.md).

The opportunity inferred from this comparison is continuity: a mock identifies a gap, the plan recommends a Lesson and fresh variants, and a delayed check shows improvement. [Original retrieval research](https://pubmed.ncbi.nlm.nih.gov/16507066/) supports measuring delayed recall; it does not validate this app's exact intervals or predict hiring success.

Defer public leaderboards, currencies, extensive badges, native mobile apps, a full application tracker, unrestricted AI chat and a peer interview marketplace until core demand is demonstrated. Certificates should describe actual completion. Do not label a composite quiz percentage “chance of passing an interview”; show quiz performance, delayed recall, explanation and practical evidence separately.

## Delivery and validation

1. Establish a baseline for onboarding, first Challenge completion, quiz outcomes, Retake completion and return sessions. Existing records cover several outcomes; navigation/abandonment need added events. Do not log keys or answer text in analytics.
2. First release: Weak Concepts, one next action, Question reporting and local reset display. Enrich variants in the Concepts surfaced by these features.
3. Second release: Placement Quizzes and goal-based plans after coverage/diagnostic rules are ready.
4. Third release: one explain-first practice format and Milestone evidence, with results feeding the plan.
5. Later: adaptive spacing, job-description mapping, reminders/PWA and private groups according to observed demand.

Primary learning measure: accuracy on previously unseen variants after a defined delay, with sample size and coverage reported. Also track repeated misconceptions, activation, seven-/28-Day returns, placement follow-up performance, report resolution time and recommendation usefulness. Use controlled comparisons only when enough Learners participate; otherwise observe usability sessions and state the evidence limits. Streak growth alone does not demonstrate learning.

If only three additions fit: **Weak Concepts with next actions, Placement Quizzes, and Question reporting**. Improve Question variation alongside them. Build goal-based planning next, followed by explain-first practice.

## Design interview: agreed direction

The Learner-facing priorities below were accepted during the design interview. They supersede the broader first-release suggestions above; detailed rules are still under discussion.

- Primary audience: experienced developers preparing for an interview soon.
- Primary learning outcome: better performance on unfamiliar Questions after a delay. Streaks and return visits are supporting measures.
- First release: Weak Concepts, one recommended next action, and Question reporting, with targeted Question variation alongside the software work.
- Placement Quizzes follow when content coverage supports a defensible diagnostic.
- Delivery constraint: keep the first release bounded. No specific development hours, maintenance budget or delivery date has been agreed.

Further accepted decisions:

- Weak Concepts reflect recent mistakes and subsequent recovery. Repeated misses on one Question do not inflate the signal; evidence is shown instead of a mastery percentage.
- Next Action priority is pending Retakes, then due Review associated with Weak Concepts, then the Unlocked Lesson. Other activities remain accessible and the recommendation is optional.
- Filing a Question Report does not change results. Admin-confirmed content defects use retirement/replacement through the existing reviewed pipeline. Treatment of historical results is still to be decided.
- Question Report is distinct from Dispute, which concerns legacy written-answer grading. These terms, Next Action and the revised Weak Concept definition are recorded in CONTEXT.md as agreed design language; their addition does not indicate feature implementation.
- Home shows one Next Action and up to three Weak Concepts with evidence and Lesson links. Each Stack page provides its fuller Concept list; sparse evidence is explicitly identified.
- A Question Report requires one category (wrong answer, ambiguous wording, outdated claim or broken Source) and permits an optional note. Reporting is available after answering; retired Questions show their retirement reason instead.
- Reports and their status are private to the reporter and Admin. Other Learners see confirmed retirement explanations through the existing content flow.
- Initial Weak Concept trigger: incorrect answers to two distinct active Questions within 30 Days. Recovery requires correct answers on three different UTC Days, covering at least two distinct active Questions, after the latest miss. Another miss restarts recovery; repeated misses on one Question do not inflate the distinct-Question count. Replays and ungraded answers provide no evidence. Expiration is displayed as no recent evidence, not recovery. These are adjustable product rules, not validated mastery thresholds.
- Preserve historical scores when a Question is retired and display its retirement explanation. Exclude retired Questions from weakness/recovery evidence and future practice. Replace a retired pending Retake with an active sibling. Retirement of the original missed Question removes its pending Retake requirement. Otherwise, if no active sibling can replace a retired pending Retake, waive that requirement with a recorded content-gap reason. The Lesson Quiz must still have passed; waiving a Retake does not award quiz points.
- Report lifecycle: Open, Accepted awaiting publication, Resolved, or Closed for a declined/duplicate report. Admin explanations are required. Accepted reports become Resolved only after the relevant retirement/replacement is imported; status updates are shown in the app.
- Initial learning measure: correctness on distinct variants with no prior recorded answer, attempted 7–14 Days after targeted practice. Report sample size and the limitation that unrecorded replays mean first recorded answer does not prove first exposure. Recommendation uptake and Retake completion are supporting measures; no interview-readiness claim is inferred.
- Tie and empty-state behavior: oldest pending Retake first; Weak Concepts ranked by distinct recent missed Questions, then most recent miss. Weak Concept Review recommendations preserve existing due-queue eligibility. With none due, recommend the Unlocked Lesson in the most recently practised Stack. If all Lessons are complete, offer ordinary due Review; otherwise show completion with Materials/Milestone links.
- Deduplicate unresolved Question Reports per Learner and Question; only Open reports are editable. Group reports per Question for Admin triage without exposing other reporters. Admin acceptance records an explanation but does not automatically publish content changes.
- Weak Concept evidence uses actually answered, recorded Questions from Lesson Quizzes, Challenges, Retakes and Review. Unanswered slots, ungraded answers, replays and retired Questions are excluded; existing Missed Question rules are unchanged. Evidence is separate per Learner and Stack, using UTC Days. Deactivation hides guidance; reactivation restores guidance from still-relevant evidence.

Implementation facts checked during the interview:

- Recorded Answers allow distinct Question IDs and first recorded attempts to be derived. Challenge replays are not recorded and cannot count as recovery. A first recorded attempt is not proof the Question has never been seen.
- Review accepts Questions in its full current due queue; targeted recommendations must preserve this eligibility. A Question tagged to a Locked Lesson can still qualify through a recorded miss or a played Challenge.
- Retirement removes Questions from Review and new Challenge answers, but does not recalculate finished Challenge scores. Pending Retakes can currently still ask a retired waiting Question; the original-Question fallback can also be retired. This conflicts with the glossary's statement that retired Questions cannot be answered and needs an explicit resolution.
- No Question Report or Dispute implementation was found; Dispute is glossary language only.

The design interview's decision frontier is closed. The consolidated design and acceptance checks are in [next-release-spec.md](next-release-spec.md); the request to use to-tickets advances them to ticket planning. The [proposed breakdown](practice-guidance-ticket-plan.md) awaits review before GitHub publication. No implementation has been authorized. The consequential retirement tradeoff is recorded in ADR-0009.
