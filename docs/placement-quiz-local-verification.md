# Local Placement Quiz verification

Run: 12 October 2026, Asia/Dhaka, `codex/placement-quizzes`. No merge, deployment, production database operation or production load test was performed. Unrelated working changes and the existing API on port 8000 were preserved.

## Actual browser flow

The local app used Next on localhost:3000, its API on 127.0.0.1:8012 and the isolated `placement_local` database. The existing disposable Clerk development learner `mock-sanity-20261011+clerk_test@example.com` signed in through Clerk's email-code method and onboarded into all four Stacks. This was real Clerk verification, without an authentication bypass or inference key.

All four Week entries, starts, saved answers, refresh/resume, submissions and results were exercised through browser controls. Expected answers came from dummy-only fixture inspection, then were entered through the interface; no production learner data was used.

| Stack | Result | Progress |
| --- | --- | --- |
| Android | Pass, 19/20; every Lesson at least 4/5 | Four placement completions; Week 2's first Lesson unlocked |
| Agentic AI | Fail, 23/25; first Lesson 3/5 | No completion; normal Lesson path retained |
| Full Stack .NET | Pass, 19/20 | One dummy prior completion preserved; three new placement completions; next Week unlocked |
| Full Stack Web | Fail, 18/20; first Lesson 3/5 | No completion; failed result accessible from Week entry |

Optional Review visibly contained all six misses: one Android, two Agentic AI, one .NET and two Web. Skipping through them created no scored answers. Dummy-only database verification confirmed four submitted attempts, 85 placement Answers, eight Completed Lessons (seven by placement and one pre-existing fixture), zero Retakes, zero Milestone ticks and zero Daily Challenge plays. Daily scores and Streaks were therefore unaffected.

Desktop and a mobile viewport override were checked. Requested override was 390×844; Chrome's current scaling reported CSS widths around 469–488. Final document/client widths matched, with no horizontal overflow. Native physical-device testing was not performed. Radio/checkbox labels, fieldset legends and keyboard activation were exercised. A deliberate local API interruption produced a visible unsaved-answer warning and disabled submission; restarting the owned API and clicking Retry saved the answer without losing the draw.

Browser findings corrected in the final slice: default graph Week hubs now link to Week detail; placement code fences retain their lines; question fieldsets fit narrow viewports; failed results can be reopened from the Week entry. Fresh Next generated types also required removing Review's optional default page argument, consistent with the earlier Stacks correction.

Screenshots are retained under `.scratch/placement-quizzes/` locally: Android mobile result/completion, Agentic AI desktop failure, .NET desktop pass and Web desktop failure. They contain only dummy evidence. Raw browser screenshots and fixture selection files are not release assets.

## Automated and HTTP evidence

- Full backend suite: 789 passed in 709.44 seconds, using isolated `placement_test` on explicit IPv4.
- Final full frontend suite: 263 passed across 65 files. Sixteen focused navigation/placement/Review checks also passed. The production build, final typecheck and lint passed.
- Final targeted backend verification after the failed-result link: 11 passed across submission, lifecycle and shipped pilot selection.
- Strict mypy: all 125 configured files passed. Ruff lint/format: 157 files passed after adding the repeatable local smoke. Content schemas match the models.
- All committed Stacks passed reviewed-content checks against baseline 79120fc. Deliberate Concept-repeat warnings identify the two new Android variants. Their official-source verification is recorded in the pilot coverage note.
- A fresh isolated `placement_import` database migrated to 0030 and imported every committed version twice; the second import reported unchanged content.
- The repeatable HTTP smoke (`api/scripts/placement_local_smoke.py`) passed unsigned/admin access checks, ordinary practice exposure, owner isolation, parallel starts/saves/abandonment, save-versus-submit, duplicate concurrent submissions, consistent pass/fail completion and fresh draws of all four shipped plans. Signed fixture identities use the normal RSA verifier; these checks are separate from the real Clerk browser flow.
- Focused tests cover insufficient fresh coverage, pending Retakes, exact-match multiple select, unanswered Questions, per-Lesson failure despite overall pass, immutable submission, preservation of old completion, frozen Challenges, retirement/teaching cancellation, actual new-Syllabus allowance reset and cached content across a two-session import boundary.

## Release limits

The entry flag remains off by default in source and has only been enabled in the owned local verification process. Production rollout needs separate authorization. Later Weeks have no reviewed placement coverage. Some fresh pools contain exactly five suitable Questions; existing exposure or abandonment may exhaust eligibility. Historical unrecorded views cannot be reconstructed. The coverage review is explicitly attributed to Codex, without claiming human Admin approval. This is a self-assessment pilot, not certification or an anti-cheating control.
