# Practice-guidance implementation progress

Branch: `codex/practice-guidance`. User authorized sequential implementation, a commit and push for each completed ticket, and automatic continuation after usage-limit resets. Deployment and merging to main are outside scope.

Order: **01 → 02 → 07 → 03 → 04 → 05 → 06 → 08**. Specification: [next-release-spec.md](next-release-spec.md). Commands and local ticket paths: [practice-guidance-implementation-order.md](practice-guidance-implementation-order.md).

| Ticket | State | Verified commit / push |
| --- | --- | --- |
| 01 Retirement-safe Retakes | Verification in progress | Candidate `6aeb067`; push pending |
| 02 Weak Concept evidence | Queued | — |
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
- Standards/spec review completed and fixes re-reviewed without blockers. API lint/format/mypy pass; 33 focused Retake/migration checks pass, including independent concurrent transactions. All 203 frontend tests, lint, typechecking and production build pass. A final full API run is in progress. The initial full run passed 645 tests and exposed two issues already corrected and verified by focused checks (isolated concurrency seed commit and migrated column comment).
- No production database migration or deployment has been run. API tests use dedicated `learning_test`, including temporary isolated schemas for genuine concurrent transactions.
