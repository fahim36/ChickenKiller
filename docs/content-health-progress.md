# Content health release progress

Branch: `codex/content-health`. Baseline: main `1f72d05`. Approved scope: [release spec](content-health-release-spec.md).

## Implemented on 11 October 2026

- 32 new MC/MS scenario variants across all four Stacks. The 16 target Concepts each have four active Questions; the total is 2,942. Existing Questions are unchanged, and no Syllabus or released Challenge was modified.
- Admin-only imported-content dashboard with Concept coverage, current Lesson quiz composition, retired-only/untested distinctions, unresolved report counts and original Source access dates. Settings links to the dashboard.
- Separate weekly/on-demand/changed-content Actions link checks for Materials and active Question Sources. Bank-only changes select their Stack. Probes are deduplicated; blocked access remains unknown, broken/unreachable checks fail, and readable/JSON artifacts survive failed probes. Redirect loops are classified as unreachable.
- The dashboard links to repository Actions reports; no external probes run during app requests and no results are imported into the database.

## Verification

- Primary-source research for all 16 Concepts: [source notes](content-health-variant-sources.md). Python and .NET examples checked; Kotlin contracts checked against official documentation.
- Content validation against `1f72d05` passes all Stacks with only deliberate sibling warnings. No answer-length warnings. Independent audit confirms 32 additions, four siblings per target, 2,942 active Questions and unchanged baseline Questions.
- Four production-import/Review tests pass, covering all 32 new Questions with ordinary completion eligibility and grading.
- Three API dashboard tests pass; all 12 link-report tests pass, covering status classification, deduplication, redirects, retries, failed-report saving and changed-bank selection.
- Frontend: 238 tests pass, lint/typecheck pass, production build passes with `/admin/content-health`.
- Backend: all 723 tests pass (11m52s locally). Lint, formatting, strict mypy and committed schema validation pass.
- Standards and spec reviews completed. Their redirect-loop finding is fixed with regression coverage. No remaining blocking findings.

## Delivery

Implementation commit: `56944c0`. Reviewed report follow-up: `56b0219`. Final verification record is committed with this file. Push to `origin/codex/content-health`; merge and deployment require a subsequent request. Ordinary CI runs on pull requests or main, so a feature-branch push alone does not create a CI run. No live external link check is claimed by these deterministic tests; scheduled/on-demand checks produce the availability artifacts.
