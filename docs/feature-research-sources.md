# Interview preparation feature research

Research date: 10 October 2026. Sources are official product pages or original research. Product observations below describe advertised capabilities; they do not establish effectiveness or an exhaustive competitor audit. Recommendations are design inferences for ChickenKiller, based on its existing daily challenges, syllabus quizzes, missed-question review, fixed three-day repeats, and self-marked milestones. Local inspection by the main analysis found that Weak Concepts and Placement routes are not implemented; those are opportunities rather than existing features.

## Observed product capabilities

| Product | Verified capability | Implication for ChickenKiller |
| --- | --- | --- |
| LeetCode | Its Top Interview 150 plan contains 150 classic questions, topic coverage, editorials, a suggested preparation duration of at least three months, and a completion badge. [Official plan](https://leetcode.com/studyplan/top-interview-150/) | Structured question lists and badges are established features. Another fixed list would have limited distinctiveness. A personal plan should change when a learner struggles or has limited time. |
| HackerRank | Preparation kits are grouped into one week, one month, and three months, with 21, 54, and 104 challenges respectively. [Official preparation kits](https://www.hackerrank.com/interview/preparation-kits) | A preparation deadline is a useful planning input, but fixed-duration kits alone are commonplace. |
| HackerRank | Current mock interviews include technical screen, coding, system design, behavioral, AI fluency, React frontend, and Node backend. Sessions are timed; the product advertises feedback on code, approach, and communication, plus discussion of feedback with the virtual interviewer. [Official mock interviews](https://www.hackerrank.com/mock-interviews) Its help center documents both voice and chat interaction. [Official help](https://help.hackerrank.com/articles/8988753946) | A generic AI interviewer is already a competitive category. An interview mode should connect its findings to the existing concept graph and a small, specific remediation plan. |
| Aced, formerly Exponent | Peer matching considers availability and practice needs; users switch interviewer and interviewee roles, exchange rubric feedback, and can practice with a friend. Technical sessions have shared editors. Some interview types offer transcripts and AI rubric feedback. [Official practice page](https://www.tryexponent.com/practice?src=homepage) | Peer matching entails scheduling and community density. Start with an asynchronous explanation workflow or a friend link before building a matching marketplace. |
| interviewing.io | Anonymous human practice uses audio/chat and a coding environment, followed by detailed feedback. Its AI interviewer covers coding and system design. [Official homepage](https://interviewing.io/) Public replays show complete interview scenarios across coding and design. [Official replays](https://interviewing.io/mocks) | Feedback and realistic explanation matter beyond answer selection. A lightweight attempt replay and reflection page can exploit ChickenKiller's existing learner history. |

## Learning evidence and limits

Roediger and Karpicke's original experiments compared repeated study with free recall of prose passages. Prior testing improved retention on delayed tests, while repeated study increased confidence; the task was not a software interview. [Original paper abstract and DOI](https://pubmed.ncbi.nlm.nih.gov/16507066/). This supports testing delayed recall and distinguishing confidence from measured recall. It does **not** establish that any particular spaced-repeat interval, multiple-choice mastery threshold, or AI score predicts hiring success.

## Recommendations inferred from this research

1. **A next-action plan tied to evidence.** Collect target role, date, minutes per day, and a brief diagnostic. Build today's mix from due reviews, prerequisite gaps, and unfamiliar questions. Explain each recommendation: "You missed event-loop ordering twice; try a fresh trace before promises." Preserve the shared daily challenge as a separate communal activity. Validate increased delayed accuracy and reduced abandoned sessions rather than claiming interview readiness.
2. **Evidence-backed mastery.** Separate attempted, quiz-passed, delayed-recall-demonstrated, and application-demonstrated states. Let a user keep self-ticked milestones but clearly distinguish them from observed performance. Use unfamiliar variants and delayed checks so retaking the same six questions cannot by itself certify mastery.
3. **Optional explain-first practice.** Ask for a short answer or a spoken explanation before revealing options. Include follow-ups such as "Why?", "What changes under this constraint?", and "Give a counterexample." Start with curated rubrics and self-review. Keep optional coaching separate from deterministic quiz pass/fail: the latest local ADR intentionally moved away from written grading because of cost and failure modes.
4. **A mistake-to-remediation loop.** Learners label whether a miss involved misconception, careless reading, timing, or an unfamiliar application. A review page links the specific lesson, a new variant, and a later check. Implement the missing Weak Concepts view and connect it to actions instead of adding only a generic mistake notebook.
5. **An interview sprint.** Build a short timed mixed round using existing questions, then report evidence for reasoning, correctness, and weak concepts. Attach two or three follow-up tasks to the result. Full coding execution, live voice, collaborative editing, and peer scheduling should come later because their operational scope is much larger.
6. **Role-specific preparation with source provenance.** Add frontend/backend/full-stack presets and optional job-description skill mapping. Show the mapped skills and let the learner correct them. Use administrator-reviewed question drafts for missing coverage rather than publishing generated questions automatically. Avoid unsupported company-frequency claims.

## Features not justified as immediate priorities

- More badges, a larger generic question catalog, or another fixed roadmap do little to establish a distinctive value proposition.
- A public leaderboard can favor volume and prior knowledge; evidence of learning is a better initial outcome measure.
- A full peer interview marketplace requires enough concurrent users, moderation, no-show handling, and scheduling. A practice-with-a-friend link tests demand with less scope.
- A single percentage labeled "interview readiness" would imply predictive validity that neither the existing quiz data nor this research establishes. Show its components and uncertainty instead.

## Suggested validation

The main repository analysis counted 976 of 1,246 Stack-local concepts with at most two active questions. Fresh transfer questions and diagnostic coverage therefore require bank enrichment before strong mastery claims; prioritize variants for high-traffic concepts and retain administrator review.

Compare a small cohort using the evidence-based daily plan with the existing flow. Measure completed sessions, fresh-question performance after a delay, repeated misconception rate, and usefulness ratings. Test explanation practice separately; do not infer success from streaks, time spent, or AI scores alone.
