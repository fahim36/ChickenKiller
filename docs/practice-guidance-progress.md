# Practice-guidance implementation progress

Branch: `codex/practice-guidance`. User authorized sequential implementation, a commit and push for each completed ticket, and automatic continuation after usage-limit resets. Deployment and merging to main are outside scope.

Order: **01 → 02 → 07 → 03 → 04 → 05 → 06 → 08**. Specification: [next-release-spec.md](next-release-spec.md). Commands and local ticket paths: [practice-guidance-implementation-order.md](practice-guidance-implementation-order.md).

| Ticket | State | Verified commit / push |
| --- | --- | --- |
| 01 Retirement-safe Retakes | Complete | `6aeb067`, `f5221e2`; pushed to `origin/codex/practice-guidance` |
| 02 Weak Concept evidence | Complete | `1b6ccb9`; pushed to `origin/codex/practice-guidance` |
| 07 Question variants | In progress | Research and coverage selection next |
| 03 Home Next Action | Queued | — |
| 04 Private Question Reports | Queued | — |
| 05 Admin report triage | Queued | — |
| 06 Resolution after import | Queued | — |
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
- Next: ticket 07. Research official sources, select two thinnest Concepts per Stack, append permanent Question variants and create bank-only Syllabus versions. Verify ordinary Quiz/Retake/Review availability, review, commit and push before ticket 03.
- No production database migration or deployment has been run. API tests use dedicated `learning_test`, including temporary isolated schemas for genuine concurrent transactions.
