# Content health and Question variants

Agreed on 11 October 2026. Work on `codex/content-health`, starting from main `1f72d05`. Preserve unrelated work. This release implements the next bounded content-health step; deployment is a separate action.

## Accepted scope

1. Add **32 new Questions**, one multiple-choice and one multiple-select scenario variant for each of 16 thin Concepts, four per Stack. Each target currently has two active Questions and should have four afterward. Use reviewed primary Sources, current teaching Lessons and existing Materials where possible. Preserve committed Questions and released Challenges, permanent IDs and existing grading rules. New written Questions are prohibited.
2. Add an **Admin-only Content Health dashboard** of imported content: active Question and Concept counts, thin Concept counts and drill-down, current Lesson coverage and quiz composition, original Source access dates, unresolved Question Report counts, and access to existing Admin maintenance pages. Report raw evidence, with no aggregate quality/mastery score. Keep the existing hard minimum of two siblings; four is an enrichment target, not a new publishing gate.
3. Extend **scheduled/on-demand link checking** to both Materials and Question Sources. Deduplicate probes, classify blocked checks separately from broken/unreachable links, and save readable and JSON reports as Actions artifacts. Probe results are availability evidence, not factual claim verification. Keep external probes out of ordinary CI and dashboard requests.
4. The dashboard links to saved **Actions reports**, rather than importing or storing probe results in the app. Distinguish imported app coverage from committed repository link-check evidence; display neither unchecked links as healthy nor Source access dates as recent revalidation dates.
5. Correct the content-links pull-request discovery gap: changes confined to a question-bank file must select its Stack for checking. Reuse existing content checks, preserve Material checking for Syllabus changes, and retain historical-version checks where applicable.

## Audited baseline

Committed content on main, not an independent production inventory. All four latest Syllabuses are `v2026-10-10`. `content-check content --today 2026-10-11` passes all four Stacks.

| Stack | Active Questions | Concepts | Exactly 2 Questions | Exactly 3 | 4+ |
| --- | ---: | ---: | ---: | ---: | ---: |
| Agentic AI Engineer | 1,104 | 468 | 316 | 136 | 16 |
| Android Developer | 604 | 290 | 271 | 14 | 5 |
| Full Stack Web Dev | 598 | 249 | 151 | 96 | 2 |
| Full Stack .NET Developer | 604 | 296 | 287 | 6 | 3 |
| Total | 2,910 | 1,303 | 1,025 | 252 | 26 |

No declared Concept currently has fewer than two active Questions. Source access dates range from 26 September through 10 October; they are original research provenance. A working URL does not establish that its claim remains current. Live report counts require the imported database, not this inventory.

## Bounded targets

All targets have exactly two active Questions, current teaching Lessons and resolving Materials. None overlaps the eight Concepts enriched in the previous release.

| Stack | Concept IDs |
| --- | --- |
| Agentic | `mutable-default-argument`, `late-binding-closures`, `w02-l03-blocking-calls`, `w02-l04-cancellation-cleanup` |
| Android | `kotlin-nullability-platform-types`, `coroutinescope-vs-supervisorscope-failure`, `swallowed-cancellationexception`, `standard-vs-unconfined-test-dispatcher` |
| Web | `w01-l03-composite-focus`, `w02-l02-validation`, `w02-l03-credential-mode`, `w02-l04-cookie-flags` |
| .NET | `boxing-hidden-interface-conversion`, `linq-deferred-multiple-enumeration`, `sync-over-async-context-deadlock`, `span-memory-arraypool-ownership` |

Expected batch result: 2,942 active Questions; target Concepts each 2→4. Coverage alone does not establish question quality or learning improvement.

## Verification and completion

- Meaningful rule/API/UI checks for aggregation, retired-only/untested Concepts, current/removed Lessons, quiz mix, original Source dates, unresolved report statuses, non-Admin access and empty/unavailable data.
- Mocked network checks for redirects, blocked statuses, missing links, transport failures/retry and deduplication, with deterministic saved reports and no real network in tests.
- Changed-bank and changed-Syllabus workflow selection checks; report artifacts survive failed probes.
- Full content checks and baseline immutability checks; deliberate sibling warnings only, no new written Questions or answer-length cues.
- Import checks show all 32 variants in eligible Quiz/Retake/Review content. Review both implementation and authored content; run appropriate full suites once at completion.
- Commit and push verified work on the feature branch. Do not merge or deploy without a subsequent request.
