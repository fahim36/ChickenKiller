---
name: update-syllabus
description: Run a Syllabus Update for one Stack. Researches the field against primary sources, then writes a new Syllabus version with its changelog and adds, retires or re-tags Questions in the Stack's append-only Question Bank. Writes nothing when nothing changed.
argument-hint: <stack-id>
arguments: [stack]
disable-model-invocation: true
allowed-tools: Read Write Edit Glob Grep WebSearch WebFetch Agent Bash(uv run --project api content-new-version *) Bash(uv run --project api content-diff *) Bash(uv run --project api content-check *) Bash(git status *) Bash(git log *) Bash(grep *)
---

# Syllabus Update: `$stack`

You are running a Syllabus Update (see `CONTEXT.md`) for the Stack `$stack`: research where its field stands today, then write a **new Syllabus version** and the Question Bank changes it needs, so that the whole Stack passes the content check. Every change is reviewed by the Admin before any Learner sees it (`docs/adr/0001-*`), so your output is files for review and a report, never a commit.

This may run headless (`claude -p`), where nobody can answer a question. **Never ask.** When a choice is unclear, take the conservative option (keep the item, keep its ID, keep the Question) and name the choice in your final report.

Before any tool call: if the Stack id in the title above is blank, reply only "Usage: `/update-syllabus <stack-id>`" and stop.

Read first: `docs/content-format.md` (the format, the Question Bank, the changelog, permanent IDs), `docs/adr/0004-*` (the append-only Question Bank) and [question-bank-rules.md](question-bank-rules.md) (how to write a Question).

## What you may change

- **The Syllabus** is versioned. You write a new version; a committed version folder is never edited.
- **The Question Bank**, `content/$stack/question-bank/*.json`, is the Stack's and is **append-only** against git `HEAD`. A committed Question (one in `HEAD`) is never edited or deleted. You may only:
  - **add** a new Question, with a new ID;
  - **retire** a committed Question: add `retired: {reason, replaced_by, on}` (`on` is today in UTC; `replaced_by` is the new Question that replaces it, or `null` if none does);
  - **re-tag** a committed Question: change only its `lesson`, when its Concept is now taught by another Lesson. Re-tag rather than write a copy.
- A Question written in this run (not in `HEAD`) is yours until the Admin commits it: edit or delete it freely.

The content check refuses anything else, naming the Question.

## 1. Find where the Stack stands

- The Stack's versions are the folders in `content/$stack/` named `v…` (versions sort by date, then `.N`). The newest one is the **current version**.
- Run `git status --porcelain content/$stack`. If the newest version folder is untracked, it is an update already in progress: carry on in that folder, and skip creating one in step 4. Changes to `question-bank/` in the same output are that update's too.
- **No version folder yet: this run creates the Stack.** Its first Syllabus comes from the plan in the repo if there is one (for `agentic-ai-engineer`, `AI-Agent-Remote-Job-Plan.md`), otherwise from your research alone.

Done when you know the current version (or that there is none) and which folder you will write.

## 2. Read the whole Question Bank

Read every file in `content/$stack/question-bank/`. Build an index, per Lesson of the current version, of:
- each Concept (`id`, `name`) and the Questions that test it;
- which Questions are live and which are retired (with their reasons);
- the highest Question number each Lesson prefix has used (`<lesson-id>-qNN`), retired Questions included.

Questions may sit in any file and test Concepts declared in any file: index by each Question's `lesson` and `concept` fields, never by file name.

Done when the index covers every Question in the bank. You use it to keep verdicts about the bank exact (step 3), to give sub-agents what their Lessons already test (step 6), and to avoid repeating a Concept by accident.

## 3. Research

Hold each Week of the current version, and the live Questions tagged to it, against high-trust primary sources fetched in this run: official docs, release notes, specifications, papers, vendor docs. Look for what is out of date, wrong, missing (a tool or practice the field now expects), or no longer worth a Learner's time. Fan out one sub-agent per Week, or per group of Weeks. Give each one its Weeks from `syllabus.json` and the live Questions tagged to their Lessons, and have it return findings with their URLs.

For a new Stack, research what the role's interviews and job posts ask for, then design the Weeks, Lessons, Milestones and Materials in the format of `content/schema/syllabus.schema.json`.

**The default verdict is *keep*.** An item changes only when a primary source fetched in this run shows the current content is wrong, out of date, or missing something the field now expects. Wording you would merely write differently is *keep*. This makes a re-run on unchanged sources change nothing.

Done when every Lesson and every live Question has a verdict.

Each Lesson's verdict is one of:
- *keep*;
- *revise* (what changes, and the source);
- *remove* (why, and the source);
- *new* (a Lesson to add: why, and the source);
- *short* (fewer than 8 live Questions, or fewer than 4 multiple choice and 2 written: it needs Questions, even if its content is kept).

Each live Question's verdict is one of:
- *keep*;
- *retire* (the reason, and the source that shows it is wrong or out of date);
- *re-tag* (the Lesson that now teaches its Concept).

Every verdict except *keep* and *short* carries at least one primary-source URL fetched in this run.

### No change

If every Lesson's and every Question's verdict is *keep*, the update is **no change**. Stop here: run nothing that writes, create no version folder, and report "no change", listing the sources you checked for each Week. This is how a re-run on unchanged sources changes nothing.

## 4. Start the new version

```bash
uv run --project api content-new-version $stack
```

It copies the current version's `syllabus.json` to a new folder named for today (`v2026-09-26`, or `v2026-09-26.1` for a second version that day) and starts its `changelog.json`. It prints the folder's path. Every item you don't touch keeps its permanent ID because it is a copy. The Question Bank is not copied: it stays in `content/$stack/question-bank/`.

A Syllabus Update that changes only the Question Bank still starts a new version: the new version is what puts its new Questions into the Review of Learners who already completed those Lessons (an Updated Lesson, `docs/content-format.md`).

Write the Syllabus only inside the new folder.

## 5. Edit the Syllabus

Apply the Lesson verdicts to the new folder's `syllabus.json`, following [Permanent IDs](#permanent-ids). Write it back as JSON with 2-space indent, UTF-8 and a final newline.

## 6. Change the Question Bank

Apply the verdicts, following [question-bank-rules.md](question-bank-rules.md):

| Verdict | What the bank gets |
|---|---|
| Lesson *new* | 8–12 new Questions tagged to it, over 3–6 new Concepts. |
| Lesson *revise* | New Questions for what changed. Every live Question the revision makes wrong or out of date is retired, `replaced_by` the new Question on its Concept. The Lesson ends with at least 8 live Questions. |
| Lesson *short* | New Questions until it meets the minimums in the rules. |
| Lesson *remove* | Each live Question tagged to it is re-tagged to the Lesson that now teaches its Concept, or retired with the reason "Its Lesson was removed: …" and `replaced_by: null`. |
| Question *retire* | `retired: {reason, replaced_by, on}`, and a new Question on the same Concept when the Concept is still taught. |
| Question *re-tag* | Only its `lesson` changes. |

Retire and re-tag committed Questions yourself, in the file where each one already is.

Write new Questions with sub-agents, each with a few Lessons (a Week at most). Give each one:
- the new version folder's path;
- its Lessons' IDs and verdicts, and your research findings for them;
- from your index: the Concepts and live Questions those Lessons already have, and the next free Question number for each;
- the path of `question-bank-rules.md`.

Each sub-agent:
- adds new Questions only, to `content/$stack/question-bank/<lesson-id>.json` for its own Lessons (creating the file if there is none), and never changes a Question already in the file;
- returns the Materials it needs added, as `{id, title, url, type, subject}`;
- returns, for each Lesson, the Questions it added and the sources it fetched.

Then add the returned Materials to the new `syllabus.json` yourself. When two agents propose the same URL, keep one ID and point both agents' Questions at it.

Done when every verdict is applied and every Lesson of the new version has enough live Questions.

## 7. Write the changelog

```bash
uv run --project api content-diff content/$stack/<new-version>
```

It lists two things:
- the Syllabus: every item added, changed and removed by permanent ID, compared with the version before;
- the Question Bank since `HEAD`: every Question added, retired and re-tagged.

Fill in the new folder's `changelog.json` (format in `docs/content-format.md`):
- `summary` says what this version changes and why, in a few sentences, and ends with the Question Bank counts from the diff ("Question Bank: 24 added, 3 retired, 2 re-tagged.");
- `changes` has one entry for every Lesson in the Syllabus diff, with the same `change` (`added`, `changed` or `removed`) and at least one source URL. You may add entries for other Syllabus items (a Material whose URL moved, say). Every entry must match the diff.

Questions get no changelog entries: each new Question carries its own Sources, each retirement its reason and replacement, and the Admin reviews them in the bank diff. A version that changes only the bank has an empty `changes`.

Read the diff as a review:
- Each Syllabus `removed` must be something you meant to remove. A `removed` plus an `added` that are really one item revised mean you gave it a new ID: restore the old one.
- Each bank line must be a verdict you applied. A Question you didn't mean to touch must match `HEAD` again.

## 8. Check

```bash
uv run --project api content-check content/$stack
uv run --project api content-check --links content/$stack/<new-version>
```

Fix every error and run the check again. A dead link gets the same page's current URL from its publisher, or a replacement Material. A warning that a site refused the check (HTTP 401, 403 or 429) is fine.

Done when the check reports **no errors** and none of these warnings:
- "no Questions yet";
- "the correct choice … is clearly the longest": rewrite that new Question's choices.

A warning that a new Question repeats a Concept is fine only if the repeat is deliberate (say, a replacement for a Retired Question); otherwise give the Question its own Concept.

## 9. Report

End with:
- the new folder's path;
- the diff's counts: the Syllabus (added, changed, removed) and the Lessons changed; the Question Bank (added, retired, re-tagged);
- every judgement call you made while nobody could be asked;
- anything the Admin should look at before committing.

Or, for no change: "no change", and the sources you checked.

Leave committing to the Admin.

## Permanent IDs

Learner progress is keyed by `(stack id, permanent id)` and has to survive every version (`docs/content-format.md`). So:

- **Revised keeps its ID.** Rewording, correcting, updating, moving to another Week: the same Syllabus item keeps the same ID. (A committed Question is never revised: it is retired and replaced.)
- **New gets a new ID, only for new content.** Formats:
  - Weeks: `w01`, ...
  - Lessons: `w01-l01`, ...
  - Milestones: `w01-m01`, ...
  - Questions and Concepts: see [question-bank-rules.md](question-bank-rules.md)
  - Materials: a slug of the title

  An ID is a name, not a position. A Lesson inserted third in Week 3 takes the next unused number, such as `w03-l06`, and a Lesson moved to Week 4 keeps `w03-l02`.
- **A removed ID is never reused**, not even for the same kind of item. Before you mint an ID, check that nothing in the Stack has used it: `grep -rl '"<id>"' content/$stack/`. The content check only catches an ID that comes back as a different kind.
