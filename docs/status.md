# Version 1 status

Where the build of version 1 stands, what is still missing, and what to do next. Written 2026-09-27 on branch `scaffold-v1`. The design is the Daily Challenge redesign ([docs/implementation-order.md](implementation-order.md), ADRs [0003](adr/0003-daily-challenge-is-the-core-loop.md)–[0006](adr/0006-grading-runs-the-claude-code-cli.md)); terms follow [CONTEXT.md](../CONTEXT.md).

## Progress

Every open ticket is built on `scaffold-v1`. #10 and #11 were closed as not planned. At the last merge (`a4a0b35`) all of these pass: 527 API tests, 146 web tests, ruff, mypy, eslint, the web build, `content-schema --check` and `content-check`.

| Ticket | What is built |
|---|---|
| #1 Walking skeleton | FastAPI + Postgres + Alembic API, Next.js web app, Render Blueprint and [deploy guide](deploy.md). Not live yet (see To do). |
| #2 Content check | `content-check` for format, permanent IDs, Concepts with fewer than two Questions and Material links (`--links`); pre-commit hook; CI jobs. |
| #3 Invite-only sign-in | Clerk session tokens checked on every request, Invitations, Admin page, a clear refusal for anyone not invited. |
| #4 Onboarding | Any number of Active Stacks, picked at onboarding and changed in Settings; deactivating keeps progress. No time zone: every Day is UTC. |
| #5 Week map | Weeks, Lessons and Milestones; lock states come only from Completed Lessons; Milestone ticks are saved. |
| #6 Lesson Quiz | 4 multiple choice + 2 written, graded on the server; skips seen and Retired Questions where the bank allows; 80% Pass Mark unlocks the next Lesson. |
| #7 Grading written answers | One `Grader`, run by the Claude Code CLI (`claude -p`, Haiku 4.5, no tools) on the API's machine ([ADR-0006](adr/0006-grading-runs-the-claude-code-cli.md)); cost logged; a failed grading can be resubmitted. |
| #8 Explanations and Retakes | Missed Questions show the Learner's answer, the correct answer or Model Answer, the Explanation, Sources and Materials; Retakes on sibling Questions. |
| #9 Review | An optional page in sets of up to 10 across Active Stacks: Missed Questions first, then spaced repeats (last answered 3+ UTC Days ago). No rounds, timers or blocking. |
| #12 `/update-syllabus` | Rewritten for the append-only bank: reads the whole bank, only adds, retires or re-tags Questions, writes "no change" when research finds nothing. |
| #13 New Syllabus version | An import keeps Completed Lessons, Missed Questions, Milestone ticks, Streaks and Daily Challenge results; Updated and removed Lessons handled. |
| #15 Question Bank with Sources | One append-only bank per Stack (`content/<stack>/question-bank/`); every Question has Sources; Retired Questions; the check rejects edits and deletions against the git baseline. |
| #16 Upcoming Challenges | `/write-challenges`, Challenge files, frozen from 00:00 UTC on their Day, "Challenges written through <date> (<n> Days left)" in the check and on an Admin page. |
| #17 Today's Daily Challenge | Released at 00:00 UTC, first try scored, Explanation and Sources after each answer, misses become Missed Questions, replays change nothing. |
| #18 Streaks and Result Card | A Streak per Active Stack from Challenges finished on their Day; a copyable Result Card such as `Agentic AI Engineer #1 · 27 Sep · 2/3 ✅❌⬜` (⬜ = ungraded). |
| #19 Archive and Catch-up | Every released Challenge back to #1; Archive plays are scored but never count toward a Streak; Retired Questions show their reason and replacement; Catch-up lists unplayed Challenges. |

### Content

- **Agentic AI Engineer**: 16 Weeks, 80 Lessons, Syllabus version `v2026-09-26.1`.
- **Question Bank**: 920 Questions. 878 are tagged to Lessons, each Lesson has 8–12, and together they cite 1,380 Sources fetched on 2026-09-26. The other 42 were written for the Daily Challenges.
- **Daily Challenges**: #1–#7, 2026-09-27 to 2026-10-03.
- **Fixed during the Sources pass**, before the bank was locked:
  - w01-l05-q03: the keyed answer was wrong.
  - Wording in w02-l04-q12, w10-l05-q08, w12-l05-q03 and w12-l03-q05.
  - One Material title.

## Gaps

Found by the code review of `scaffold-v1` against `main` on 2026-09-27.

### Against the documented standards

- [ ] **No Playwright tests.** [build-plan.md](build-plan.md) asks for one per milestone demo from M2 on.
- [ ] **No grader eval set.** [build-plan.md](build-plan.md) M4 asks for 30+ labelled written answers and a CI check on agreement.
- [ ] **Clock reads that bypass `Now`.** `api/app/learners.py:54` and `api/app/onboarding.py:83` call `datetime.now(UTC)` directly.
- [ ] **Local date.** `api/app/content/new_version.py:87` uses `date.today()` instead of the UTC date (ADR-0005).
- [ ] **Stale build plan.** [build-plan.md](build-plan.md) still describes the old grading: "pending grade" regraded later, and a score plus missed key points. The grader now returns pass/fail with one line of feedback, and a failure is resubmitted (ADR-0003, ADR-0006).
- [ ] **Glossary.** The home page says "Add or drop Stacks"; CONTEXT.md says deactivate.
- [ ] **Duplicated code worth tidying.** Judgement calls, not bugs:
  - the answer forms in `ReviewFlow` and `DailyChallengeFlow`;
  - the `status` logic of `ChallengeState` and `ArchivedChallenge`;
  - the "released" comparison and the `ChallengePlay` join in `challenges.py`;
  - `Answer.context` strings spread over four modules;
  - `main.py` (about 830 lines) mixing routes, mapping and label formatting.

### Against the tickets

- [ ] **#1: not live.** The app has no public URL yet (see To do).
- [ ] **#2: link check.** Material links are checked only by the `Content links` workflow (weekly, and on PRs that touch `content/`), not by the pre-commit hook or the main CI job.
- [ ] **#15/#16: direct pushes.** A push straight to `main` compares content against itself, so CI can't catch an edited or deleted Question or Challenge. Pull requests are checked properly. Fix it by comparing with the previous commit on push, or by requiring PRs into `main`.
- [ ] **#12/#16: headless untested.** "Runs headless (`claude -p`)" is documented in the README but hasn't been run. "Re-running on unchanged sources changes nothing" is an instruction in the skill, not something a test enforces.
- [ ] **#13: changed-Lesson test.** The test's "changed Lesson" only gains a Question. No end-to-end test changes a Lesson's title or topics; that path is unit-tested only.
- [ ] **#17: errors look like "No Challenge today".** If the home page's request for today's Challenge fails, the card still says "No Challenge today".
- [ ] **#3: route coverage.** The no-token test covers four routes. Every other route is protected by the router-wide dependency, but no test walks all routes.

### Small edge cases

- [ ] **Updated with nothing new.** A Lesson is marked Updated even when a new version only retired Questions or re-tagged them away, so there is nothing new for Review.
- [ ] **Missed Question with no sibling.** If a Missed Question's Concept has no sibling left, its Retake is skipped. The content check prevents this, but nothing enforces it at runtime.
- [ ] **All Questions retired.** If every Question of a Day's Challenge is retired, that Day can't be played and breaks the Streak.
- [ ] **Slow grading holds a lock.** Grading, which takes up to 45 s, runs while the Learner's Stack row is locked, so a second answer on that Stack waits.
- [ ] **Two Written Questions graded one at a time.** A Lesson Quiz with two written answers takes about 20 s to submit. Grading them in parallel would halve that.

## To do

### Steps only the owner can do

- [ ] **Sign-in (Clerk).** Create a Clerk application with Email and Google, add the session-token claim `{"email": "{{user.primary_email_address}}"}`, and set the keys ([deploy.md](deploy.md#sign-in-with-clerk)).
- [ ] **Public URL (Render).** Apply the Blueprint in `render.yaml` ([deploy.md](deploy.md)). A hosted API has no Claude Code, so written answers can't be graded there (ADR-0006); run the API locally to grade them.
- [ ] **Pre-commit hook.** Run `uvx pre-commit install` in your clone.
- [ ] **Branch protection.** Make `CI / content` a required check, and require PRs into `main`. Requiring PRs also closes the direct-push gap above.

### Next development

- [ ] Fix the review gaps above, starting with the clock reads, the UTC date, the build-plan wording, the error-versus-"No Challenge today" display and the direct-push check.
- [ ] Add Playwright tests for the milestone demos and the grader eval set.
- [ ] **Local use.** A local mode that skips sign-in and treats the owner as the Admin, and one command that starts the database, imports content and runs both servers.
- [ ] Run `/write-challenges agentic-ai-engineer <days>` before 2026-10-01, when fewer than three Days are left.
- [ ] Open a PR from `scaffold-v1` to `main`, then close the finished issues.

### Content decisions for the owner

- [ ] **Week 11** aims at agent security (prompt injection, the "lethal trifecta"), but none of its Lessons teaches it.
- [ ] **Week 6** is titled "LangGraph in depth", but its Lessons are coding-interview topics; LangGraph appears only in its Milestones.
- [ ] **Handbook Questions.** w06-l05 and w14-l05-q09/q10 ask what the Tech Interview Handbook says, so they cite the handbook itself. Keep them, or retire them for Questions on the underlying advice.

### Choices made during the build, to confirm or change

- **Deactivating.** The last Active Stack can't be deactivated.
- **Streak timing.**
  - A Challenge started before 00:00 UTC and finished after it doesn't count for its Day.
  - Today's Challenge played from the Archive still counts toward the Streak.
  - Days while a Stack was deactivated still break its Streak.
- **Review.**
  - Spaced repeats are Questions last answered 3 or more UTC Days ago.
  - Sets are drawn fresh on each load, not stored.
- **Catch-up** leaves out today's Challenge and lists newest first.
- **Grading** uses `--effort low`, a 45 s timeout and a $0.05 budget cap per call.
