# Placement Quiz implementation order

Approved breakdown. Design confirmed on 12 October 2026. Tickets published as #29–#34 in fahim36/ChickenKiller.

User authorized implementation of the approved tickets sequentially, local-instance testing, a commit and push for every completed ticket on a feature branch, and continuation after natural usage-limit resets. No main merge or deployment is authorized. Preserve unrelated working changes and do not overlap another active implementation run.

## Recommended order

**01 → 02 → 03 → 04 → 05 → 06**

| Ticket | Delivers | Genuine blockers |
| --- | --- | --- |
| 01 | Reviewed coverage import and Admin eligibility gaps | None |
| 02 | Exposure tracking throughout ordinary practice | None |
| 03 | Eligible start, autosave/resume, reservations and cancellation | 01, 02 |
| 04 | Atomic submission, results, completion and Review | 03 |
| 05 | Reviewed Week 1 content for all four Stacks | 01 |
| 06 | Complete local pilot verification and operation guide | 04, 05 |

The order is convenient for sequential execution, not a forced dependency chain. Ticket 02 is independent of 01; content ticket 05 can run once 01 is complete. The release gate stays closed until submission and reviewed content are verified together.

## Execution requirements

- Resolve and record a baseline containing the approved practice-guidance, content-health and mock-interview foundations. Create a dedicated placement feature branch without silently merging or committing unrelated work.
- Publish approved tickets to the configured GitHub tracker with ready-for-agent labels and native blocking edges. Add verified issue links to this order document.
- Work only tickets whose blockers are complete and present in the checkout. Implement one ticket at a time, verify locally, commit and push before advancing.
- Keep a progress checkpoint containing the active ticket, baseline, commits, checks and unresolved work. Resume that checkpoint after a natural usage reset; do not purchase resets or credits.
- Continuation must first check whether another run is active and avoid concurrent tests against shared databases. Notify only on meaningful completion, failure or required user action; stay quiet while blocked by an unchanged usage window.
- Use local-instance dummy-account testing. Do not drop databases, copy production data, expose credentials, deploy or merge merely to verify tickets.
- After all six verified pushes, stop the continuation automation and report completion with test evidence and any remaining rollout limitations.

