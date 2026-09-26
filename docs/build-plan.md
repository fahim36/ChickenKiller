# Build plan: Learning App version 1

Version 1 is six milestones. Each one ends with something you can show a person in under five minutes, tests that prove it works, and a paragraph for your portfolio. The tickets are GitHub issues #1–#13 on [fahim36/InterviewCrackerAssistant](https://github.com/fahim36/InterviewCrackerAssistant/issues), and [implementation-order.md](implementation-order.md) says which ticket blocks which. Terms follow [CONTEXT.md](../CONTEXT.md).

| Milestone | Tickets | Demo in one line |
|---|---|---|
| [M0 Scaffold](#m0-scaffold-done) | parts of #1, #2, #12 | The 16-week Syllabus loads from files and shows in the browser |
| [M1 Live skeleton](#m1-live-skeleton) | #1, #2 | A public URL, and a commit with broken content is refused |
| [M2 Your own Learner](#m2-your-own-learner) | #3, #4 | An invited Learner signs in and activates one or more Stacks |
| [M3 The core loop](#m3-the-core-loop) | #5, #6 | Study a Lesson, pass its quiz, watch the next one unlock |
| [M4 Learning from mistakes](#m4-learning-from-mistakes) | #8, #7 | A wrong answer is explained; the Retake asks a sibling Question |
| [M5 Review](#m5-review) | #9 | A Missed Question comes back in Review until it's right on three Days |
| [M6 A Syllabus that updates itself](#m6-a-syllabus-that-updates-itself) | #12, #13 | Claude Code rewrites a Lesson; the Learner's progress survives |

#12 runs alongside M2–M5. Real Question Banks mean every quiz milestone is tested and demoed on real content, not placeholders.

## How every milestone is tested

- **Domain rules are plain functions with a fake clock.** Unlocking, Pass Mark, Review's three-Days rule and Streaks take the time or the Day as an argument, and every Day turns at 00:00 UTC (ADR-0005). Tests can then say "it is 23:59 UTC" without waiting or patching time.
- **API tests** run FastAPI's test client against a real Postgres (Docker Compose locally, a service container in CI). The database is built from the Alembic migrations and seeded from a small content folder (`api/tests/conftest.py`). Each test's writes are rolled back.
- **Component tests** use Vitest and Testing Library in `web/`.
- **The demo script is an end-to-end test.** From M2 on, each milestone's demo is also a Playwright test that clicks through the same steps. If the test passes, the demo will work live.
- **CI** (`.github/workflows/ci.yml`) runs all of it on every pull request, plus the content check on every committed Stack version.

---

## M0 Scaffold (done)

**What exists:**
- a Next.js 16 front end;
- a FastAPI backend with Alembic migrations, and Postgres in Docker Compose;
- the content format as Pydantic models, with the JSON Schema in `content/schema/` generated from them;
- the content check;
- the importer.

Each imported Syllabus version is stored as its own set of rows. Rows carry permanent IDs, and the newest version is current. The 16-week Agentic AI Engineer syllabus is converted into content files: 80 Lessons, 169 Milestones, 115 Materials, and Question Banks for Week 1's five Lessons.

**Tests:** 31 pytest tests cover:
- each content-check rule;
- importing twice changes nothing;
- changed content under an imported version is refused;
- a newer version becomes current;
- the Lesson response never includes answers;
- the committed content passes;
- the JSON Schema files match the models;
- the migrations match the models.

There are also 11 Vitest tests for the page helpers, the components and the Lesson page.

**Demo:**
1. `docker compose up -d`, then import the content. The check runs first and prints its one warning: 75 Lessons have no Question Bank yet.
2. Open the Stack page. Show that Week 1 adds up to 15 hours, and Milestones are tagged Build or Job hunt.
3. Open a Lesson (`/stacks/<stack>/lessons/<lesson>`). Show the topics, the exercise, the Materials with their type labels, and the previous/next links.

**Portfolio note:** "Content is code." The Syllabus lives in version-numbered files that are reviewed like any pull request. A schema plus semantic checks run before every commit: every Concept has a sibling for Retakes, and every Material a Lesson refers to exists.

## M1 Live skeleton

**Tickets:** finish #1 (deployment) and #2 (content check runs as a pre-commit hook and in CI).

**Build:**
- Deploy the web app, the API and a managed Postgres, then run the importer against production as a release step. The config is ready: `render.yaml` and `api/Dockerfile`, whose start runs `api/release.sh` (migrate, then import). The remaining human steps are in [deploy.md](deploy.md).
- Turn on the `content-check` pre-commit hook and a `--links` job that runs each week.

**Tests:**
- A smoke test hits `/health` and one Lesson on the deployed URL after each deploy.
- Content-check tests for the hook's exit code.
- The links job's HTTP calls are replaced with a fake: a dead link is an error, a blocked site only a warning.

**Demo:**
1. Open the public URL on your phone.
2. In the terminal, change an answer to a choice that doesn't exist and try to commit. The commit is refused, and the message names the Question.

**Portfolio note:** a deployed walking skeleton with CI from the first day. Mention what the deploy costs per month and how long a cold start takes.

## M2 Your own Learner

**Tickets:** #3 invite-only sign-in, #4 onboarding.

**Build:**
- Clerk sign-in with an allow-list of invites.
- A Learner record created on first sign-in.
- Onboarding activates one or more Stacks, each an Active Stack with its own Lessons and progress. Settings activates and deactivates them later; a deactivated Stack keeps its progress. There is no time zone: every Day is a UTC Day (ADR-0005).

**Tests:**
- The API rejects requests without a valid token, and rejects valid tokens whose email isn't invited.
- Onboarding is required before any Lesson page.
- Onboarding with several Stacks, and deactivating then reactivating a Stack with its progress intact.

**Demo (Playwright):** invite an email, sign in, pick "Agentic AI Engineer", land on the home screen, and open its Week map.

**Portfolio note:** authentication handed to a hosted provider (ADR-0002), and why that was the right trade for a one-person project.

## M3 The core loop

**Tickets:** #5 Week map with lock states, #6 Lesson Quiz (multiple choice) and unlocking.

**Build:**
- The Week map shows each Lesson as Completed, Unlocked or Locked.
- A Lesson Quiz picks 4 multiple-choice Questions from the Question Bank, covering different Concepts.
- Scoring 80% or more makes it a Completed Lesson and unlocks the next one.

**Tests:**
- Unlocking follows completion only. The date doesn't matter: a Learner can do three Lessons in one day or one in a week.
- The quiz never repeats a Concept while an unused one remains.
- Answers are checked on the server; the client never receives `answer`.
- The Pass Mark boundary: 79% fails and 80% passes.

**Demo (Playwright):**
1. Lesson 2 is locked.
2. Study Lesson 1 and take its quiz. Get one wrong and still pass.
3. Lesson 2 unlocks.

**Portfolio note:** "Completion-based, not calendar-based." Explain why the app has no time limits but still enforces the order.

## M4 Learning from mistakes

**Tickets:** #8 Explanations and Retakes, #7 grading written answers.

**Build:**
- After a quiz, each Missed Question shows its Explanation and links to its Materials.
- A Retake asks a sibling Question on the same Concept.
- Written answers are graded against the Model Answer's key points by one Claude call (the only runtime Claude call, ADR-0001). The grader returns a score and the key points the answer missed.

**Tests:**
- A Retake never asks the original Missed Question, and never the same sibling twice while an unused one is left.
- Once every sibling is used they cycle again, never the same one twice in a row. A Concept with exactly two Questions has one sibling, so its Retakes ask that sibling again (#8).
- A sibling may be of either type: a missed written Question gets a Retake like any other, and a written Retake is graded the same way as in the Lesson Quiz (a grading failure records nothing and the Learner answers again).
- Grading is tested with the Claude client replaced by a fake. Separately, **a small eval set**: 30 or more written answers you've labelled pass or fail. Measure how often the grader agrees with your labels, and fail CI if agreement drops below the number you set.

**Demo:**
1. Answer a written Question badly on purpose.
2. Show the grade, the key points you missed, the Explanation and the Material link.
3. Take the Retake and see a different Question on the same Concept.

**Portfolio note:** this is the AI-engineering section of the write-up. It covers:
- the grading prompt and its output schema;
- the eval set and the grader's measured agreement;
- the cost per graded answer;
- what happens when the Claude call fails: the answer is saved as "pending grade" and graded again later.

## M5 Review

**Tickets:** #9 Review. (#10 Rounds 2 and 3 and #11 the Daily Review Streak were closed: see ADR-0003.)

**Build:**
- Review is one optional page across all Active Stacks, in sets of up to 10 Questions, answered one at a time. It has no rounds or timers and never blocks anything.
- Missed Questions come first, oldest first. Then the Updated Lessons' new Questions, then spaced repeats: Questions of Completed Lessons (and, from #17, played Daily Challenges) not answered in the last 3 Days, least recently answered first.
- A Missed Question leaves the queue once it has been answered correctly on 3 different Days since it was last missed.
- A wrong answer shows its Explanation (and, from #15, its Sources). Retired Questions are never drawn.

**Tests (all fake-clock):**
- A Missed Question answered correctly on Days 2, 3 and 4 leads each of those Days' sets and is gone on Day 5.
- A Question answered correctly twice on one Day counts as one Day; the Day turns at 00:00 UTC.
- A spaced repeat answered today comes back three Days later.
- With Missed Questions waiting in Review, the next Lesson's quiz still starts.

**Demo:**
1. Miss a Question in a Lesson Quiz.
2. Open Review: the Missed Question comes first, from whichever Stack it belongs to.
3. Answer it wrongly and read the Explanation; the next set asks it again.
4. Move the demo clock forward a Day at a time: three correct Days take it out of the queue.

**Portfolio note:** a small, fully tested scheduling rule. Show how Review stays optional (no stored sets, nothing to finish) and how the fake-clock tests cover the three-Days rule across Day boundaries.

## M6 A Syllabus that updates itself

**Tickets:** #12 `/update-syllabus` and the first Stack (started in M0), #13 importing a new Syllabus version without losing progress.

**Build:**
- The `/update-syllabus` Claude Code command researches each Lesson, writes a new version folder, and adds, retires or re-tags Questions in the Stack's Question Bank.
- The importer adds that version beside the old one and appends to the Question Bank (ADR-0004).
- Learners keep their progress by permanent id: Completed Lessons, Missed Questions and Milestone ticks all carry over.
- A Lesson changed since the Learner completed it, or a new Lesson added behind them, is an Updated Lesson. It is marked on the Week map, its new Questions go into Review, and it never locks anything.
- A removed Lesson leaves the path. A Learner who completed it keeps it in their history. Its Questions stay in the Question Bank, retired, re-tagged or tagged to no Lesson, and no Lesson Quiz draws them; a Missed Question among them that isn't retired stays in Review. If it was their furthest Completed Lesson, the next surviving Lesson after it unlocks.
- A Lesson Quiz in progress finishes on the old version; the next attempt uses the new one.

**Tests:**
- Import v1, record progress, then import v2 (with one Lesson added, one changed and one removed).
- Completions survive. The changed Lesson, and the new Lesson added behind the Learner, are Updated Lessons, and their new Questions come in Review after the Missed Questions. The removed Lesson's Questions stay in the bank, and a Missed Question among them stays in Review. Each Learner's Unlocked Lesson is still correct.
- The content check passes on the generated folder.

**Demo:**
1. Show a Learner partway through Week 1.
2. In the terminal, run `/update-syllabus` for one Lesson and review the diff it wrote.
3. Commit and import.
4. Refresh as the Learner: their progress is still there, and the updated Lesson has an "Updated" badge.

**Portfolio note:** the headline story. It covers:
- An agent in the terminal is the content pipeline, while the app itself makes only one runtime model call (ADR-0001).
- Its output is checked by code before any person sees it.
- Versioned content lets the Syllabus change every week without breaking anyone's progress.

---

## Portfolio write-up outline

Use this once M6 is finished. Each section can reuse the milestone notes above.

1. **The problem:** keeping interview preparation current in a field that changes every month, and staying consistent without a teacher.
2. **What it does:** a 90-second screen recording of the M3 → M5 demos joined together.
3. **Architecture:** Next.js → FastAPI → Postgres; Claude Code writes the content repo; the importer reads it. Reuse the diagram in the README.
4. **Three decisions and their trade-offs:** ADR-0001 (the content pipeline), ADR-0002 (the stack), and completion-based unlocking.
5. **The hard parts:** the Daily Challenge's shared Day boundary, the grader's eval, and importing a new version without losing progress.
6. **Numbers:**
   - test count and CI time;
   - the grader's agreement on the eval set;
   - cost per graded answer and per Syllabus Update;
   - how many of your own Lessons you completed using it.
7. **What's next:** the version 2 list from [implementation-order.md](implementation-order.md#version-2-and-later-not-ticketed-yet).
