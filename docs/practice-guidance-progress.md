# Practice-guidance implementation progress

Branch: `codex/practice-guidance`. User authorized sequential implementation, a commit and push for each completed ticket, and automatic continuation after usage-limit resets. Deployment and merging to main are outside scope.

Order: **01 → 02 → 07 → 03 → 04 → 05 → 06 → 08**. Specification: [next-release-spec.md](next-release-spec.md). Commands and local ticket paths: [practice-guidance-implementation-order.md](practice-guidance-implementation-order.md).

| Ticket | State | Verified commit / push |
| --- | --- | --- |
| 01 Retirement-safe Retakes | Complete | `6aeb067`, `f5221e2`; pushed to `origin/codex/practice-guidance` |
| 02 Weak Concept evidence | Complete | `1b6ccb9`; pushed to `origin/codex/practice-guidance` |
| 07 Question variants | Complete | `ca3a0f1` and validation fix; pushed to `origin/codex/practice-guidance` |
| 03 Home Next Action | Complete | `d8254d9`, `eca5f1d`, `f8729ae`; pushed to `origin/codex/practice-guidance` |
| 04 Private Question Reports | Complete | `f8065ca`, `8289299`, `1937f12`; pushed to `origin/codex/practice-guidance` |
| 05 Admin report triage | Complete | `20cdcfc`, `8c87bfa`; pushed to `origin/codex/practice-guidance` |
| 06 Resolution after import | Complete | `12528bd`; verified, push checkpoint below |
| 08 Delayed outcomes | Queued | — |

## Continuation

Heartbeat automation `resume-practice-guidance-tickets` checks every 30 minutes. It checks usage limits before continuing, leaves an already-running implementation alone, and resumes from this log. Notify on meaningful completion, failed push or required user action; stay quiet while limits/progress are unchanged. Stop the follow-up when every ticket is verified and pushed.

## Current checkpoint

- Created the feature branch from `08eb271` on main; existing unrelated content and scratch work must remain untouched.
- Agreed test seams are the ticket's API, rule and UI acceptance boundaries.
- Planning commit `aff9a4e` is pushed. Git's cached credential denied access; the already-active `fahim36` GitHub CLI account works. Push with `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push origin codex/practice-guidance` if the credential cache still differs.
- Ticket 01 stores waiver/replacement reasons separately from Answer evidence. Retrieval and submission reconcile retirement; stale displayed Questions return ungraded replacement results. PostgreSQL attempt locks serialize completion and duplicate submissions.
- Ticket 01 is complete. Final verification: **649 API tests passed**; API lint, formatting and strict mypy passed; **203 frontend tests passed**, with frontend lint, typechecking and production build passed. Standards/spec review and follow-up review have no remaining blockers.
- Ticket 02 is complete at `1b6ccb9`: **662 API tests passed**, API lint/formatting/strict mypy passed; **207 frontend tests passed**, frontend lint/typechecking/production build passed. Standards and Spec reviews found no remaining issues. The private endpoint `/stacks/{stack_id}/concept-evidence` and Stack views distinguish weak/recovered/expired/insufficient evidence with counts, dates and current teaching links.
- Ticket 07 implementation `ca3a0f1` adds sixteen sourced MC/MS Questions: two thinnest Concepts per Stack, all eight now 2 → 4 active Questions. Four `v2026-10-10` versions preserve existing Lessons; the web Stack adds a sequence-function Material. Three upcoming Challenges schedule untagged variants for 20–21 October. Existing Questions and released Challenges remain unchanged. Coverage/source notes are in `docs/practice-guidance-variant-coverage.md` and `docs/practice-guidance-variant-sources.md`.
- Ticket 07 content-check against `3601b16` passes all four Stacks with only deliberate sibling warnings; no answer-length warning. All content diffs match the intended additions. API lint, formatting and strict mypy pass. Standards/Spec follow-up reviews have no remaining findings; Python print choices, distinct setval reset behavior and source notes were corrected in the local candidate. Python traces and a PostgreSQL temporary-sequence reset trace were verified.
- Ticket 07 is verified: all four import-to-Review tests passed for all sixteen variants; all eight committed-content checks passed (eleven checks passed together, the longest import passed separately after refreshing its expired fixture token). API lint/formatting/strict mypy and both final reviews pass. Content-check against ticket baseline passes all Stacks. The existing multi-version import test now refreshes the normal signed-in Learner token after lengthy imports, preserving authentication checks.
- Ticket 03 is complete at `d8254d9` and `eca5f1d`: **677 API tests passed**, API lint/formatting/strict mypy passed; **214 frontend tests passed**, frontend lint/typechecking/production build passed. The final Home failure-handling fix passed all 13 Home tests plus lint/typechecking. Standards and Spec reviews have no remaining blockers. Home offers one optional action, up to three Weak Concepts and current teaching links. Targeted Review filters before pagination without changing answer eligibility; pending Retake links open the specific attempt even for a removed Lesson. Guidance loading failures preserve access to activities.
- Ticket 04 is complete at `f8065ca` and `8289299`: **687 API tests passed**, lint/formatting/strict mypy passed; **222 frontend tests passed**, lint/typechecking/build passed. The final deferred-save fix also passed three report-form tests and lint/typechecking. Standards and Spec follow-up reviews have no remaining blockers. Private reports support four categories, optional notes, recorded-answer eligibility, retirement explanations, Open-only edits and a private status list. A partial unique index and genuine concurrent-request test enforce one unresolved report per Learner/Question. Report writes leave scores, Streaks and completion unchanged. Schema migration `0020_question_reports` is tested only in `learning_test`.
- Ticket 05 is complete at `20cdcfc`: **690 API tests passed**, lint/formatting/strict mypy passed; **227 frontend tests passed**, lint/typechecking/build passed. Standards and Spec reviews have no findings. Admin reports are grouped by Question, decisions require explanations and can only move Open reports to Accepted/Closed. Genuine concurrent decisions cannot overwrite each other; reporter edits share the report lock. Acceptance changes no content, scores or completion. No database migration was needed for 05.
- Next: ticket 06, associate accepted reports with an exact expected retirement/replacement and resolve only when that correction is imported and committed. Verify unrelated/failed imports and retries, then review, commit and push before ticket 08. Untracked variant working helpers are not deliverables; do not rerun write-variants.py (it appends another batch) or stage unrelated scratch work.
- No production database migration or deployment has been run. API tests use dedicated `learning_test`, including temporary isolated schemas for genuine concurrent transactions.

- Ticket 06 candidate `12528bd` implements Admin correction associations, matching retirement/replacement verification and transactional import-linked resolution. All 17 focused report/migration checks pass, API lint/formatting/strict mypy pass, 230 frontend tests and production build pass, frontend lint/typechecking pass. Standards and Spec reviews have no findings. Full API suite is running; do not mark complete or push until it passes.

- Ticket 06 is complete: **693 API tests passed**, API lint/formatting/strict mypy passed; **230 frontend tests passed**, lint/typechecking/production build passed. Standards and Spec reviews have no findings. Migration `0021_report_corrections` verified in learning_test. Resolution changes commit with the matching content import and roll back if later import checks fail; retries preserve resolution timestamps. Next: ticket 08 delayed outcomes. No deployment or production migration performed.
