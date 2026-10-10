# Practice-guidance implementation progress

Branch: `codex/practice-guidance`. User authorized sequential implementation, a commit and push for each completed ticket, and automatic continuation after usage-limit resets. Deployment and merging to main are outside scope.

Order: **01 → 02 → 07 → 03 → 04 → 05 → 06 → 08**. Specification: [next-release-spec.md](next-release-spec.md). Commands and local ticket paths: [practice-guidance-implementation-order.md](practice-guidance-implementation-order.md).

| Ticket | State | Verified commit / push |
| --- | --- | --- |
| 01 Retirement-safe Retakes | Complete | `6aeb067`, `f5221e2`; pushed to `origin/codex/practice-guidance` |
| 02 Weak Concept evidence | In progress | Pending |
| 07 Question variants | Queued | — |
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
- Next: ticket 02, Weak Concept evidence. Keep rule tests at the agreed pure-rule seam and API/UI acceptance checks. Use recorded actually answered, graded outcomes from the four existing contexts; calculate the current and preceding 29 UTC Days; recovery must be strictly after the latest miss and require three UTC Days across two Questions. Exclude retired Questions, and distinguish expiration from recovery. Preserve authorization and current-Syllabus Lesson link handling.
- No production database migration or deployment has been run. API tests use dedicated `learning_test`, including temporary isolated schemas for genuine concurrent transactions.
