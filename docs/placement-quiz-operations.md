# Placement Quiz pilot operations

The pilot covers Week 1 in the four shipped v2026-10-10 Syllabuses. Five equally weighted MC/MS Questions per Lesson cover every reviewed essential Concept. Passing requires the shared 80% Pass Mark overall and in every Lesson. Multiple select uses an exact match; unanswered Questions are misses. This is an untimed self-assessment.

## Publication and release

Apply migrations through 0030, then import the committed content. Reviewed plans live at `content/<stack>/<syllabus-version>/placement/w01.json`; inspect `/admin/placement-coverage` or the Admin coverage page. All four Week 1 plans must report valid. Later Weeks intentionally have no plans.

Published plans are immutable within their Syllabus. Changing or removing one requires a new Syllabus version and the usual reviewed-content checks. Adding a first plan to a version without one is supported. New Questions are append-only and need sourced claims, an explanation, reviewed distractors and current source-verification dates. Keep frozen Challenge Questions available; placement pools exclude them.

`PLACEMENT_ENABLED=true` enables the learner entry in the web server. Keep it unset until backend migrations, valid imported coverage and local acceptance checks are present together. Authenticated placement API routes remain implemented independently of this entry flag. Existing owner-only attempts can still resume when the entry flag is off. Enabling the entry requires restarting/rebuilding the web process for its environment; no production rollout has been performed here.

## Allowance and progress

Only the earliest incomplete Week is eligible, and pending Retakes in it block start. Placement tests every Lesson, including previously completed ones. A pass inserts only missing completion records; their private attempt links identify Completed by placement. Existing completion timestamps, versions and methods are preserved. Updated Lessons remain completed and do not reopen a finished Week. Milestone ticks, Daily scores and Streaks are independent.

One submitted attempt is allowed per Week teaching revision, including failure. Lesson teaching, substantive referenced material information or essential coverage changes alter the revision. Question-pool additions, reviewer changes and link-only fixes do not. A new revision permits another attempt only while the Week remains incomplete and sufficient unseen coverage exists. Failed result links remain available from the Week entry; passing evidence links are attached to newly completed Lessons.

Submission locks the learner's practice, revalidates content, eligibility and reservations, then commits scoring, submission, optional Review misses, reservation release and completion together. Concurrent requests return one immutable result. Saving after submission cannot edit it. Passing and failing misses enter optional Review and create no compulsory Retakes.

## Exposure and unfinished attempts

Prompt/options delivery records first exposure across ordinary practice and placement. Migration 0028 backfills historical answered Questions; older unrecorded prompt views cannot be reconstructed. Freshness never falls back to seen Questions. Some pilot pools are minimal, so prior exposure or abandonment may make placement unavailable; continue the normal Lesson path in that case.

A draw reserves its Questions before delivery. Existing in-flight quizzes, pending Retakes and frozen/upcoming Daily Challenges are excluded. Other practice cannot expose a reserved Question. Study, Daily Challenges and Review remain available; target-Week Lesson Quizzes/Retakes wait until resume or abandonment.

Saved answers and the exact draw resume without expiry. Save failures remain visible and block final submission until recovered. Abandonment consumes no submitted allowance and releases reservations, while viewed Questions stay seen. Changed teaching or a drawn Question's retirement cancels an unfinished attempt on its next read/write/delivery; cancellation also retains exposure. Content import and practice selection share database locks to avoid stale selection during import.

## Repeatable local verification

Run `uv run --project api python api/scripts/placement_local_smoke.py` from the repository root. It uses only the local `placement_local` database on 127.0.0.1:5433 and an HTTP instance on 127.0.0.1:8011, with signed fixture identities through the ordinary RSA verifier. It migrates/imports without dropping a database, uses a reusable exposure-check learner and unique lifecycle learners, checks concurrent lifecycle/submission behavior and draws the four shipped plans. This fixture run is distinct from live Clerk sign-in.

For pytest, use a separate database such as `placement_test` with explicit IPv4. The repository test fixture rebuilds that designated test database, so never point TEST_DATABASE_URL at learner data. Do not overlap runs against the same database. Preserve other tasks' local servers and unrelated working changes. See `placement-quiz-local-verification.md` for actual browser and suite evidence.
