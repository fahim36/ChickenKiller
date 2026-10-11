# Placement Quiz implementation progress

Authorized: finish all six approved tickets sequentially, test on the local instance, and commit/push each ticket on the feature branch. Resume after natural usage resets; no reset credit spending, main merge or deployment.

Branch: `codex/placement-quizzes`. Baseline: `79120fc` from the completed mock-interview branch, including practice guidance and content health. Preserve unrelated working changes.

Automation: `resume-placement-quiz-tickets`, active hourly thread heartbeat. Do not overlap an active implementation turn or shared-database tests. Pause after all verified pushes.

| Ticket | Issue | Blockers | State |
| --- | --- | --- | --- |
| 01 | #29 | None | Complete: 57731c3 pushed |
| 02 | #30 | None | Verified; commit/push in progress |
| 03 | #31 | #29, #30 | Not started |
| 04 | #32 | #31 | Not started |
| 05 | #33 | #29 | Not started |
| 06 | #34 | #32, #33 | Not started |

GitHub native dependency endpoint returned 404; real issue references are recorded in each issue body as the configured fallback. Local copies are in `.scratch/placement-quizzes/issues/`. Read live tickets/comments before execution.

Ticket 01: five coverage/migration checks passed against isolated IPv4 placement_test; nine focused frontend checks passed, backend strict mypy/ruff and frontend lint/typecheck passed. Isolated local HTTP instance on 127.0.0.1:8011 passed unsigned401, dummy Learner403 and signed Admin valid coverage200. Fixture identity uses normal RSA token verification with local public keys, not live Clerk login. Standards review: no findings. Spec review found mutable published plans and missing substantive material revision fields; both corrected, regression-tested and re-reviewed with no remaining findings. Published plans are immutable within a Syllabus; changes/removal require a new Syllabus. A small existing Stacks page signature correction unblocked Next generated typechecking.


Ticket 02: 113 focused exposure/Lesson Quiz/Retake/Review/Daily Challenge/migration tests passed in 144.76 seconds against placement_test via 127.0.0.1. Backend strict mypy and ruff passed. Local HTTP dummy Learner quiz delivery verified persistent exposure without submitted answers. Standards and Spec reviews found no blockers; the seen-history docstring was corrected. Historical answered Questions are backfilled; unrecorded prior views remain unknown.

Environment: use TEST_DATABASE_URL=postgresql+psycopg://learning:learning@127.0.0.1:5433/placement_test?connect_timeout=10 for pytest; localhost can hang in psycopg on this host. Local network smoke uses separate placement_local and signed fixture identities with ordinary verifier, not live Clerk. Use gh auth token --user fahim36 only inside the executing process as GH_TOKEN for push; cached/current saifulhoque-bjit account is denied. Never print tokens. The issue repo is fahim36/ChickenKiller; origin redirects from the old name.
