# Learners may grade with their own LLM key, and Claude clients connect through MCP drafts

This amends ADR-0006 and extends ADR-0001.

**Grading.** A Learner may save an NVIDIA API key in Settings; their written answers are then graded by Nemotron 3.5 Lightning (`nvidia/nemotron-3.5-lightning-30b-a3b`) through NVIDIA's OpenAI-style `/chat/completions` endpoint, with the same prompt and the same `{passed, feedback}` reply as the CLI. A Learner with no key is graded with the Admin's saved key, and with no key at all by the Claude Code CLI (ADR-0006). We chose this because the CLI only grades where the API runs next to a signed-in Claude Code, so a hosted API couldn't grade at all; a key per Learner also keeps each person's usage on their own account.

**Content from other Claude clients.** The API serves an MCP connector at `/mcp/`. Each Learner creates personal access tokens in Settings, and a token signs their Claude client in as them. The connector reads the Stacks and accepts proposed Questions and Daily Challenges as drafts recorded under the author. It never writes content: the bank and the Challenges stay in git, append-only and checked against the committed baseline (ADR-0004). The Admin accepts or rejects each draft, `content-export-drafts` writes the accepted ones to `content/<stack>/drafts/`, and /update-syllabus or /write-challenges merges them and runs `content-check`.

## Consequences

- Keys are secrets. They are encrypted with Fernet under the server's `LLM_KEY_SECRET` (rotatable: comma-separate several, the first encrypts), never sent back (only the last four characters), and never logged. Without the secret no key can be saved and grading uses the CLI. Changing the secret without keeping the old one makes saved keys unreadable; they are skipped and logged.
- Graders fall back in order: the Learner's key, the Admin's key, the CLI. NVIDIA's free endpoint usually answers in about a second but can queue a request for a minute, so a provider call has a 30 s timeout and the next grader takes over. Nemotron's thinking is turned off (`chat_template_kwargs.enable_thinking: false`): with it on, a grading took up to a minute and often ran out of tokens before answering.
- Access tokens (`ica_…`) are stored only as SHA-256 hashes, shown once, and revocable; a revoked token is refused at once. The connector has no cookies, so its DNS-rebinding Host check is off.
- Anyone signed in may propose drafts; reading the Question Bank is the Admin's only, since it includes Upcoming Challenges' Questions. No tool returns an answer or a Model Answer.

## Addendum: Gemini keys

New keys are Google Gemini API keys (free from Google AI Studio), graded by `gemini-3.1-flash-lite` through Gemini's OpenAI-compatible `/chat/completions` endpoint, with `reasoning_effort: low` (Gemini 3 can't turn thinking off, and its thinking counts toward `max_tokens`, so the limit is 2048). Keys saved earlier for NVIDIA keep working. The fallback order is unchanged.

## Addendum: own keys only

With `OWN_GRADING_KEY_REQUIRED=true` a Learner's written answers are graded only with their own saved key, so an open sign-up can't spend the Admin's key or the server's Claude Code. Without a key, grading refuses with `grading_failed` and a message to save one; nothing is recorded, not even a Daily Challenge's first try. The Admin keeps the usual fallback order.

## Addendum: building a new Stack through drafts

Any Learner may request a new Stack, from the Add a Stack button on the Stacks screen (`POST /stack-requests`) or the connector's `request_stack` tool. Claude then builds it through the connector in order, and `get_stack_plan` (or the Stacks screen) says which step it is at:

1. **Weekly plan**: `submit_syllabus` takes the Stack's whole first Syllabus as a `syllabus` draft. The newest one not rejected is the plan.
2. **Quiz setup**: `submit_questions` then takes Questions tagged to that plan's Lessons, until every Lesson has at least 8 (4 multiple choice, 2 written) and every Concept 2.
3. **Review**: the Admin accepts the drafts. Because there is no live content to merge into, `content-export-drafts` writes them as content straight away: `content/<stack>/<version>/syllabus.json` (a first version, so no changelog) and `content/<stack>/question-bank/draft-<id>.json`. `content-check` and `content-import` then make the Stack live, as for any content.

The `build_stack` MCP prompt gives Claude the whole procedure. Content still enters only through git; a Stack request is a draft of kind `stack` and changes nothing by itself. `new` is not a valid Stack id, since `/stacks/new` is the Add a Stack screen.
