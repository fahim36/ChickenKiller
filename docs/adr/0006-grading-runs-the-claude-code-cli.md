# Written answers are graded by the Claude Code CLI on the API's machine

The API grades each written answer by running Claude Code headless (`claude -p`) on the machine the API runs on, with Claude Haiku 4.5, a JSON-schema `{passed, feedback}` output, no tools, and none of the repository's CLAUDE.md, settings or hooks. We chose this over calling the Anthropic Messages API with an `ANTHROPIC_API_KEY` because this is a personal project whose owner has a Claude Code plan and no API key: grading then costs nothing beyond that plan, in line with ADR-0001's choice to keep Claude costs on the Admin's own plan.

## Consequences

- Grading only works where the API runs on a machine with Claude Code installed and signed in. Local use grades; a hosted deploy such as Render can't, and there every written answer fails with 503 `grading_failed` (multiple choice still scores, and the Learner can resubmit).
- Each grading starts a CLI process, so it takes roughly 10 s rather than 1–2 s. Grading has a timeout, and any failure is a `GradingFailed` the Learner can resubmit.
- The CLI path is `claude` on the PATH, or `CLAUDE_BIN`. On Windows it must be the native `claude.exe`.
- Grading uses the plan's usage limits. The cost the CLI reports is logged with each call.
