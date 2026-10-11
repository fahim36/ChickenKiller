# Mock interview implementation progress

Authorized: implement all eight tickets sequentially and resume automatically after natural usage resets. No reset credits, paid provider spending, main merge, deployment or production load tests.

Branch: `codex/mock-interviews`. Baseline: `e8d4b11fb05b3099f153a41616d89c9237f560c5`, including the pushed content-health release; it has not been merged to main.

Automation: `resume-mock-interview-tickets`, active every 30 minutes. Check usage limits before implementation; preserve checkpoints if a window is exhausted. Do not overlap another active implementation run.

| Ticket | Issue | Status |
| --- | --- | --- |
| 01 | #21 | Verified; implementation commits 24453a1 and 3188ce5 |
| 02 | #22 | Verified: 0df4352, 5dac168 and final test correction |
| 03 | #23 | Verified: 6332080 and c169299 |
| 04 | #24 | Verified: ee9e810 and 687d860 |
| 05 | #25 | Verified: bdfa748; Whisper disabled with documented unverified gate |
| 06 | #26 | Verified: cb57583; bounded typed and voice guided turns |
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

## Ticket 04 evidence

Main voice responses support bounded browser recording, owner-only playback, decoded format/byte/duration checks, consented own-key Gemini transcription, transcript correction/confirmation and immediate audio deletion. Upload receipts enforce one replacement even after discard. Awaiting audio expires after 24 hours; cleanup physically removes it, late provider results cannot recreate discarded recordings. Device speech keeps text visible. FFmpeg is included in the API image; Server Actions allow a deliberately bounded 5 MB transport. No live Gemini calls.

Checks: 20 audio/feedback/migration tests including a late-discard regression; eight frontend interactions; strict mypy (107 files), ruff, frontend lint/typecheck/production build. Standards review found no blockers (shared reservation-policy extraction suggested as a maintenance improvement). Spec review found stale replacement playback; corrected and regression-tested, then re-reviewed. Follow-up/retry progression and server-derived 45/60-second recording limits remain ticket 06 work; these turns are not available yet.

## Ticket 05 evidence

Whisper remains disabled: no permissioned representative corpus or deployment spare-capacity evidence is available. `docs/mock-interview-whisper-gate.md` records the infeasible benchmark decision, all unmeasured criteria and requirements before later enablement; no synthetic fixture is represented as recognition evidence. No worker, model download, production load test or new provider is installed. Authenticated path metadata and learner messaging truthfully identify Gemini audio and its shared attempt cost, with playback/typing alternatives.

Checks: 21 audio/feedback tests including zero-spend path metadata, quota18, playback preservation, no hidden retry/fallback and shared feedback budget; eight frontend interaction tests; mypy (107 files), ruff and frontend typecheck/lint. Both parallel reviews found no blockers. Ticket 05 explicitly accepts this disabled outcome; it does not promise measured Whisper performance.

## Ticket 06 evidence

Server-locked optional turn creation supports one reviewed follow-up and one main-scenario retry, requires main evidence first, enforces scenario/open-turn order and rejects duplicate/recursive turns. AI feedback selects only from reviewed options; self-review explicitly chooses reviewed content without a provider call. Follow-up/retry feedback cannot generate another follow-up. All responses stay immutable, separate from Quiz evidence, and bounded to nine; existing 18-attempt policy is reused. Voice upload/transcription derive 90/45/60 seconds from server-resolved turn kind. Teaching Lesson links and quoted evidence remain available; retries show earlier responses without an improvement/readiness claim. In-memory drafts are keyed per session/turn to avoid losing an unfinished main response when opening earlier optional practice.

Checks: 30 guided/self-review/feedback/audio/migration tests, 12 frontend interactions including draft preservation, strict mypy (109 files), ruff, frontend typecheck/lint/production build. Both parallel reviews found no blockers; a draft-preservation usability suggestion was addressed. No live provider call or Quiz evidence mutation.

Next: ticket 07. Six tickets are complete; remaining two require implementation. Automatic runs must read actual working changes before continuing.
