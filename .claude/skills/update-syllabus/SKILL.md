---
name: update-syllabus
description: Run a Syllabus Update for one Stack. Researches the field against primary sources and writes a new version folder with the Syllabus and a changelog, and Questions for every Lesson in the Stack's Question Bank.
argument-hint: <stack-id>
arguments: [stack]
disable-model-invocation: true
allowed-tools: Read Write Edit Glob Grep WebSearch WebFetch Agent Bash(uv run --project api content-new-version *) Bash(uv run --project api content-diff *) Bash(uv run --project api content-check *) Bash(git status *) Bash(git log *) Bash(grep *)
---

# Syllabus Update: `$stack`

You are running a Syllabus Update (see `CONTEXT.md`) for the Stack `$stack`: research where its field stands today, then write a **new version** of its content that passes the content check. Every change is reviewed by the Admin before any Learner sees it (`docs/adr/0001-*`), so your output is a folder for review and a report, never a commit.

This may run headless (`claude -p`), where nobody can answer a question. **Never ask.** When a choice is unclear, take the conservative option (keep the item, keep its ID) and name the choice in your final report.

Before any tool call: if the Stack id in the title above is blank, reply only "Usage: `/update-syllabus <stack-id>`" and stop.

Read first: `docs/content-format.md` (the format, the changelog, permanent IDs) and [question-bank-rules.md](question-bank-rules.md) (how to write a Question Bank).

## 1. Find where the Stack stands

- The Stack's versions are the folders in `content/$stack/`. The newest one (versions sort by date, then `.N`) is the **current version**.
- Run `git status --porcelain content/$stack`. If the newest folder is untracked, it is an update already in progress: carry on in that folder and skip creating one in step 3.
- **No folder yet: this run creates the Stack.** Its first Syllabus comes from the plan in the repo if there is one (for `agentic-ai-engineer`, `AI-Agent-Remote-Job-Plan.md`), otherwise from your research alone.

Done when you know the current version (or that there is none) and which folder you will write.

## 2. Research

Hold each Week of the current version against high-trust primary sources: official docs, release notes, specifications, papers, vendor docs. Look for what is out of date, wrong, missing (a tool or practice the field now expects), or no longer worth a Learner's time. Fan out one sub-agent per Week, or per group of Weeks, and have each return findings with their URLs.

For a new Stack, research what the role's interviews and job posts ask for, then design the Weeks, Lessons, Milestones and Materials in the format of `content/schema/syllabus.schema.json`.

Done when **every Lesson has a verdict**:
- *keep*;
- *revise* (what, and the source);
- *add a Question Bank* (it has none);
- *remove* (why, and the source);
- or it is a *new* Lesson (why, and the source).

Every verdict except *keep* carries at least one primary-source URL.

If every verdict is *keep* and every Lesson already has Questions, stop. Create nothing, and report "no update needed", with the sources you checked.

## 3. Start the new version

```bash
uv run --project api content-new-version $stack
```

It copies the current version to a new folder named for today (`v2026-09-26`, or `v2026-09-26.1` for a second version that day) and starts its `changelog.json`. It prints the folder's path. Every item you don't touch keeps its permanent ID because it is a copy.

Write the Syllabus only inside that new folder. Questions go in the Stack's one Question Bank, `content/$stack/question-bank/`, which is not versioned and is not copied. A committed version never changes: the importer refuses changed content under a version it has already imported.

## 4. Edit the Syllabus

Apply the verdicts to the new folder's `syllabus.json`, following the permanent-ID rules below. Write it back as JSON with 2-space indent, UTF-8 and a final newline.

## 5. Write the Question Banks

Every Lesson ends with a Question Bank that follows [question-bank-rules.md](question-bank-rules.md):
- a Lesson with no bank gets one;
- a new Lesson gets one;
- a revised Lesson gets new Questions to match.

The Question Bank is append-only (ADR-0004): a committed Question is never edited or deleted. One that is wrong or out of date is retired (`retired: {reason, replaced_by?}`) and a new one added, and a Question can be re-tagged to another Lesson (its `lesson`). The content check refuses anything else.

Fan out sub-agents, each with a few Lessons (a Week at most). Give each one:
- the new folder's path;
- its Lessons' IDs;
- the path of `question-bank-rules.md`;
- your research findings for those Lessons.

Each sub-agent:
- writes only `content/$stack/question-bank/<lesson-id>.json` for its own Lessons, never `syllabus.json` or `changelog.json`;
- returns the Materials it needs added, as `{id, title, url, type, subject}`;
- returns a changelog entry for each Lesson: *what* changed, *why*, and its *sources*.

Then add the returned Materials to `syllabus.json` yourself. When two agents propose the same URL, keep one ID and point both banks at it.

Done when every Lesson in the Syllabus has Questions tagged to it.

## 6. Write the changelog

```bash
uv run --project api content-diff content/$stack/<new-version>
```

This lists every added, changed and removed item by permanent ID, compared with the version before. Fill in `changelog.json` (format in `docs/content-format.md`):
- `summary` says what this version changes and why, in a few sentences;
- `changes` has one entry for every Lesson in the diff, with the same `change` (`added`, `changed` or `removed`) and at least one source URL.

You may add entries for other kinds of item (a Material whose URL moved, say). Every entry must match the diff. The changelog covers the Syllabus only: Questions added or retired aren't listed, since each carries its own Sources and retirement reason.

Read the diff as a review of your IDs. Each `removed` must be something you meant to remove. A `removed` plus an `added` that are really one item revised mean you gave it a new ID: restore the old one.

## 7. Check

```bash
uv run --project api content-check content
uv run --project api content-check --links content/$stack/<new-version>
```

Fix every error and run the check again. A dead link gets the same page's current URL from its publisher, or a replacement Material. A warning that a site refused the check (HTTP 401, 403 or 429) is fine.

Done when the check reports **no errors**, and no "no Questions yet" warning. A warning that a new Question repeats a Concept is fine if the repeat is deliberate.

## 8. Report

End with:
- the new folder's path;
- the diff's counts (added, changed, removed), and the Lessons changed;
- every judgement call you made while nobody could be asked;
- anything the Admin should look at before committing.

Leave committing to the Admin.

## Permanent IDs

Learner progress is keyed by `(stack id, permanent id)` and has to survive every version (`docs/content-format.md`). So:

- **Revised keeps its ID.** Rewording, correcting, updating, moving to another Week: the same item keeps the same ID.
- **New gets a new ID, only for new content.** Formats:
  - Weeks: `w01`, ...
  - Lessons: `w01-l01`, ...
  - Milestones: `w01-m01`, ...
  - Questions: `<lesson-id>-q01`, ...
  - Concepts: `<lesson-id>-<slug>`
  - Materials: a slug of the title

  An ID is a name, not a position. A Lesson inserted third in Week 3 takes the next unused number, such as `w03-l06`, and a Lesson moved to Week 4 keeps `w03-l02`.
- **A removed ID is never reused**, not even for the same kind of item. Before you mint an ID, check that no version of the Stack has used it: `grep -rl '"<id>"' content/$stack/`. The content check only catches an ID that comes back as a different kind.
- **Replacing is removing plus adding.** A Question rewritten to test something else is a new Question with a new ID. The old ID is gone for good.
