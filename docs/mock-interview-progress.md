# Mock interview implementation progress

Authorized: implement all eight tickets sequentially and resume automatically after natural usage resets. No reset credits, paid provider spending, main merge, deployment or production load tests.

Branch: `codex/mock-interviews`. Baseline: `e8d4b11fb05b3099f153a41616d89c9237f560c5`, including the pushed content-health release; it has not been merged to main.

Automation: `resume-mock-interview-tickets`, active every 30 minutes. Check usage limits before implementation; preserve checkpoints if a window is exhausted. Do not overlap another active implementation run.

| Ticket | Issue | Status |
| --- | --- | --- |
| 01 | #21 | Verified; implementation commits 24453a1 and 3188ce5 |
| 02 | #22 | Verified: 0df4352, 5dac168 and final test correction |
| 03 | #23 | Verified: 6332080 and c169299 |
| 04 | #24 | Next: recorded audio and explicit transcript confirmation |
| 05 | #25 | Pending |
| 06 | #26 | Pending |
| 07 | #27 | Pending |
| 08 | #28 | Pending |

Complete focused verification and review, then commit and push each ticket before advancing. Full release checks belong to ticket 08. Record evidence and unresolved limitations here. Stop the automation after all eight are verified and pushed.

## Ticket 01 evidence

Four seed prompts, separate reviewed schema/check/import, studied-topic selection, typed/skip self-review, immutable snapshots and owner-only history are implemented. A lifespan cleanup task physically deletes expired text every minute; expired sessions cannot be read or changed. No provider calls or quiz evidence changes.

Checks: eight focused content/API tests; 17 migration/import regression tests; two frontend interaction tests; strict backend mypy (100 files); backend ruff; frontend lint/typecheck/production build; all four Stacks content check against baseline. Parallel standards/spec review completed. Spec finding about mismatched teaching links corrected and re-reviewed; no remaining blockers. Standards suggested typed prompt serialization as a nonblocking maintenance improvement.

## Ticket 02 evidence

Sixteen reviewed scenarios, four distinct Concepts per Stack, and Admin-only coverage are implemented. All 16 imported topics qualify after their teaching Lessons are completed; three-distinct-topic automatic and manual sessions verified on each Stack. Repeated imports preserve 16 rows. Admin coverage reports unresolved teaching links without private evidence. Existing Questions, Syllabuses and Challenges are unchanged.

Checks: full-batch integration test passed (79 seconds), two coverage UI tests, strict mypy (102 files), ruff, frontend lint/typecheck/build and schema/content checks. Parallel standards/spec reviews found no blockers. Source claims made concrete following an editorial suggestion. Test credentials refreshed after lengthy imports; privacy assertions inspect JSON fields rather than public identifier substrings.

## Ticket 03 evidence

Own saved Gemini key explicitly enabled with free-project attestation and processing consent, fixed Flash-Lite endpoint, confirmed-text feedback, bounded structured output, exact-quote/reviewed-follow-up validation and immutable evaluated text are implemented. No legacy fallback key or provider retries. Failed attempts count toward the 18-request limit. A dedicated owner-level PostgreSQL advisory lock spans the network request independently of deletable session data. Interrupted attempts remain charged and require manual new IDs; replayed IDs never resend.

Checks: nine feedback tests including quota18, idempotency, overlap, deletion during processing, malformed provider envelopes and interrupted recovery; 29 earlier feedback/legacy grading checks; self-review/migration regression checks; four frontend interaction tests; strict mypy (105 files), ruff, frontend typecheck/lint/build. Reviews caught delete-guard and stranded-operation defects, both fixed and re-reviewed with no remaining blockers. No real Gemini requests made.

Next: ticket 04. Three tickets are complete; remaining five require implementation. Automatic runs must read actual working changes before continuing.
