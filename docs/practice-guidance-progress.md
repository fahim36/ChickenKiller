# Practice-guidance implementation progress

Branch: `codex/practice-guidance`. User authorized sequential implementation, a commit and push for each completed ticket, and automatic continuation after usage-limit resets. Deployment and merging to main are outside scope.

Order: **01 → 02 → 07 → 03 → 04 → 05 → 06 → 08**. Specification: [next-release-spec.md](next-release-spec.md). Commands and local ticket paths: [practice-guidance-implementation-order.md](practice-guidance-implementation-order.md).

| Ticket | State | Verified commit / push |
| --- | --- | --- |
| 01 Retirement-safe Retakes | In progress | Pending |
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
- Started Docker Desktop so API tests can use their dedicated Postgres test database.
- Begin ticket 01 with a failing API test for retirement of the original missed Question. Persist waiver/replacement reasons separately from correct-answer evidence; handle stale displayed Questions without grading their replacement using an old response.
