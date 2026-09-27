# Learners may grade with their own LLM key, and Claude clients connect through MCP drafts

This amends ADR-0006 and extends ADR-0001.

**Grading.** A Learner may save an NVIDIA API key in Settings; their written answers are then graded by Nemotron 3.5 Lightning (`nvidia/nemotron-3.5-lightning-30b-a3b`) through NVIDIA's OpenAI-style `/chat/completions` endpoint, with the same prompt and the same `{passed, feedback}` reply as the CLI. A Learner with no key is graded with the Admin's saved key, and with no key at all by the Claude Code CLI (ADR-0006). We chose this because the CLI only grades where the API runs next to a signed-in Claude Code, so a hosted API couldn't grade at all; a key per Learner also keeps each person's usage on their own account.

**Content from other Claude clients.** The API serves an MCP connector at `/mcp/`. Each Learner creates personal access tokens in Settings, and a token signs their Claude client in as them. The connector reads the Stacks and accepts proposed Questions and Daily Challenges as drafts recorded under the author. It never writes content: the bank and the Challenges stay in git, append-only and checked against the committed baseline (ADR-0004). The Admin accepts or rejects each draft, `content-export-drafts` writes the accepted ones to `content/<stack>/drafts/`, and /update-syllabus or /write-challenges merges them and runs `content-check`.

## Consequences

- Keys are secrets. They are encrypted with Fernet under the server's `LLM_KEY_SECRET` (rotatable: comma-separate several, the first encrypts), never sent back (only the last four characters), and never logged. Without the secret no key can be saved and grading uses the CLI. Changing the secret without keeping the old one makes saved keys unreadable; they are skipped and logged.
- Graders fall back in order: the Learner's key, the Admin's key, the CLI. NVIDIA's free endpoint usually answers in about a second but can queue a request for a minute, so a provider call has a 30 s timeout and the next grader takes over. Nemotron's thinking is turned off (`chat_template_kwargs.enable_thinking: false`): with it on, a grading took up to a minute and often ran out of tokens before answering.
- Access tokens (`ica_…`) are stored only as SHA-256 hashes, shown once, and revocable; a revoked token is refused at once. The connector has no cookies, so its DNS-rebinding Host check is off.
- Anyone signed in may propose drafts; reading the Question Bank is the Admin's only, since it includes Upcoming Challenges' Questions. No tool returns an answer or a Model Answer.
