# Ticket 07: bounded variant coverage

Baseline: `3601b16`. Research accessed 2026-10-10 UTC. Index scanned every bank file, including retired Questions, and sorted Concepts by active count then stable Concept ID. Each selected Concept had two active Questions; all ties at the minimum were resolved by ID.

| Stack | Concept | Before → after | New permanent Question IDs | Application |
| --- | --- | --- | --- | --- |
| agentic-ai-engineer | `assignment-binds-names` | 2 → 4 | `w01-l01-q11`, `w01-l01-q12` | Rebinding trace; shallow-copy cache edit |
| agentic-ai-engineer | `c001-langgraph-thread-id` | 2 → 4 | `c001-q09`, `c001-q10` | Thread-state lookup; restart durability |
| android-developer | `activity-recreation-on-config-change` | 2 → 4 | `w04-l01-q12`, `w04-l01-q13` | Default recreation; mixed Compose/View handling |
| android-developer | `activity-tasks-launch-modes` | 2 → 4 | `w04-l02-q12`, `w04-l02-q13` | Top-instance reuse; CLEAR_TOP identity |
| full-stack-web-dev | `c065-advisory-lock-lifetimes` | 2 → 4 | `c065-q07`, `c065-q08` | Stacked-lock rollback; competing scopes |
| full-stack-web-dev | `c065-sequence-allocation-and-rollback` | 2 → 4 | `c065-q09`, `c065-q10` | setval rollback and false flag; currval and conflict gaps |
| fullstack-dotnet-developer | `activitysource-trace-propagation` | 2 → 4 | `w09-l03-q12`, `w09-l03-q13` | Missing remote parent; nested async scope |
| fullstack-dotnet-developer | `adr-append-only-decision-log` | 2 → 4 | `w06-l04-q12`, `w06-l04-q13` | Erased audit rationale; changed constraints |

## Import and eligibility

Four new `v2026-10-10` versions preserve existing Lessons and their permanent IDs. Their bank-only updates make new Lesson-tagged Questions available in quizzes, same-Concept Retakes and eligible Review, including Updated Lessons after an import. The web Stack also adds the official sequence-function Material. No committed Question is edited, retired or re-tagged.

Challenge-only Concepts remain untagged because the current Syllabus teaches them through Challenges or Milestones. Their new Questions are scheduled in upcoming Challenges: agentic #24 on 20 October; web #11 on 20 October and #12 on 21 October. Only those three upcoming files change; every released Challenge remains identical. Finished first plays make these Questions eligible for ordinary spaced Review three UTC Days later. There is no eligibility bypass or new practice endpoint.

Each selected Concept gains one multiple-choice and one multiple-select Question. The five affected Lessons finish with at least six multiple-choice and three multiple-select Questions. Sources and worked scenarios are documented in [practice-guidance-variant-sources.md](practice-guidance-variant-sources.md). Deliberate sibling warnings are expected; answer-length warnings are not.

## Verification

Content-check against `3601b16` verifies all versions, append-only Questions and frozen Challenges. Import/API checks in `api/tests/test_practice_variant_content.py` exercise all sixteen new Questions through normal completion or finished Challenge eligibility and ordinary Review submission. Imports use the dedicated test database, not production.
