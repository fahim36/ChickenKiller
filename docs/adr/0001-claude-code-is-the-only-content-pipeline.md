# Claude Code in the Admin's terminal is the only content pipeline

All Syllabus content (Lessons, Question Banks, Explanations, Materials) is produced by the Admin running Claude Code in their own terminal. Claude Code writes version-numbered content files into the repository, checked against a fixed format. The Admin reviews and commits them, and an import step loads them into the app. We chose this over an in-app research agent (Claude API or Claude Agent SDK on the server) for two reasons: every change is reviewed before any Learner sees it, and research costs stay on the Admin's own Claude plan rather than billed per Learner.

## Consequences

- A Learner cannot get a newly researched Stack instantly. New Stacks arrive through Stack Requests that the Admin works through.
- The server does call Claude in exactly one place: grading written answers, through the Claude Code CLI on the API's machine (ADR-0006). That call never generates or changes content.
- Content only updates when the Admin runs Claude Code, whether by hand or from a scheduled task on the Admin's machine.
