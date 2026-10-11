# Mock interview implementation progress

Authorized: implement all eight tickets sequentially and resume automatically after natural usage resets. No reset credits, paid provider spending, main merge, deployment or production load tests.

Branch: `codex/mock-interviews`. Baseline: `e8d4b11fb05b3099f153a41616d89c9237f560c5`, including the pushed content-health release; it has not been merged to main.

Automation: `resume-mock-interview-tickets`, active every 30 minutes. Check usage limits before implementation; preserve checkpoints if a window is exhausted. Do not overlap another active implementation run.

| Ticket | Issue | Status |
| --- | --- | --- |
| 01 | #21 | Verified; implementation commits 24453a1 and 3188ce5 |
| 02 | #22 | Next: reviewed content batch and Admin coverage |
| 03 | #23 | Pending |
| 04 | #24 | Pending |
| 05 | #25 | Pending |
| 06 | #26 | Pending |
| 07 | #27 | Pending |
| 08 | #28 | Pending |

Complete focused verification and review, then commit and push each ticket before advancing. Full release checks belong to ticket 08. Record evidence and unresolved limitations here. Stop the automation after all eight are verified and pushed.

## Ticket 01 evidence

Four seed prompts, separate reviewed schema/check/import, studied-topic selection, typed/skip self-review, immutable snapshots and owner-only history are implemented. A lifespan cleanup task physically deletes expired text every minute; expired sessions cannot be read or changed. No provider calls or quiz evidence changes.

Checks: eight focused content/API tests; 17 migration/import regression tests; two frontend interaction tests; strict backend mypy (100 files); backend ruff; frontend lint/typecheck/production build; all four Stacks content check against baseline. Parallel standards/spec review completed. Spec finding about mismatched teaching links corrected and re-reviewed; no remaining blockers. Standards suggested typed prompt serialization as a nonblocking maintenance improvement.

Next: ticket 02. Only ticket 01 is complete; remaining seven require implementation. Automatic runs must read actual working changes before continuing.
