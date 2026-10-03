---
name: write-challenges
description: Write a Stack's next Upcoming Challenges. Reads the whole Question Bank, researches the field against primary sources, and writes one Daily Challenge file per Day (two multiple-choice Questions, then one multiple select), adding new Questions with Sources to the Question Bank.
argument-hint: <stack-id> <days>
arguments: [stack, days]
disable-model-invocation: true
allowed-tools: Read Write Edit Glob Grep WebSearch WebFetch Agent Bash(uv run --project api content-check *) Bash(git status *) Bash(git log *) Bash(grep *) Bash(date *)
---

# Upcoming Challenges: `$stack`, `$days` Days

You are writing the next `$days` Upcoming Challenges (see `CONTEXT.md`: Daily Challenge, Upcoming Challenge, Question Bank, Source, Concept) for the Stack `$stack`. Every change is reviewed by the Admin before any Learner sees it (`docs/adr/0001-*`), so your output is files for review and a report, never a commit.

This may run headless (`claude -p`), where nobody can answer a question. **Never ask.** When a choice is unclear, take the conservative option and name it in your final report.

Before any tool call: if the Stack id or the number of Days in the title above is blank, or the number isn't a whole number from 1 to 30, reply only "Usage: `/write-challenges <stack-id> <days>`" and stop.

Read first: `docs/content-format.md` (the Daily Challenge and Question Bank formats, the frozen rule), [question-bank-rules.md](../update-syllabus/question-bank-rules.md) (how to write a Question) and [challenge-rules.md](challenge-rules.md) (what is different for a Challenge's Questions).

## 1. Find where the Stack's Challenges stand

- Today is the UTC date: `date -u +%Y-%m-%d`. Every Day is a UTC Day (ADR-0005).
- `content/$stack/challenges/launch.json` holds the launch Day; `content/$stack/challenges/<number>.json` are the Challenges written so far. Challenge #n is on the launch Day plus n - 1 Days.
- **No `challenges/` folder: this run launches the Stack's Challenges.** Write `launch.json` with **tomorrow's** UTC date as `launch` (today has already begun, so it can't get a Challenge), and start at #1.
- Otherwise the next Challenge is the first number after the last one written. If its Day is today or earlier (the Stack ran out of Challenges), skip ahead to tomorrow's number: a Challenge is released at 00:00 UTC on its Day, so a Day that has begun never gets one, and the check refuses it.
- Run `git status --porcelain content/$stack`. Untracked Challenge files are a run already in progress: keep them, and carry on after the last one.

Done when you know the numbers and Days you will write: `$days` of them, consecutive, the first on tomorrow or later.

## 2. Read the whole Question Bank

Read every file in `content/$stack/question-bank/`: released, upcoming and Retired Questions, with their Concepts. List:
- every Concept, and how many Questions that aren't retired test it;
- every Concept a Challenge already uses (from the Questions in `challenges/*.json`);
- the Stack's newest Syllabus (`content/$stack/<newest version>/syllabus.json`), for its Lessons and Materials.

Done when you can say, for any idea, whether the bank already tests it.

## 3. Choose each Day's Concepts

Each Challenge tests **three different Concepts**. Prefer, in order:
1. a **new Concept** the bank doesn't test yet, inside the Stack's field (its Syllabus topics, or what its interviews ask now);
2. a Concept the bank tests but no Challenge has used yet.

Repeat a Concept only when nothing better fits, and name each repeat in your report. The content check warns when a new Question repeats a committed Concept, so a repeat is always visible. Spread the week across the Syllabus: not two Days on the same Lesson in a row.

Done when every Day has three Concepts, each with the reason it was chosen.

## 4. Research and write the Questions

Each Challenge is **two multiple-choice Questions, then one multiple select**, in that order in its file. Never a written Question: they are legacy ([ADR-0008](../../../docs/adr/0008-multiple-select-replaces-written-questions.md)). Write new Questions for it (reusing one from the bank is allowed but rare; see [challenge-rules.md](challenge-rules.md)), following [question-bank-rules.md](../update-syllabus/question-bank-rules.md) and [challenge-rules.md](challenge-rules.md).

Fan out one sub-agent per Day (or per two Days). Give each one:
- the Challenge numbers and Days, and each Day's three Concepts;
- the paths of both rules files and of the Syllabus;
- the Question and Concept IDs it may use. A Question with no Lesson is `c<number>-q01`, `-q02`, ... after the Challenge it is written for (`c001-q01`), and a new Concept `c<number>-<slug>`; a Question tagged to a Lesson takes the Lesson's `<lesson-id>-qNN` (see the rules).

Each sub-agent:
- fetches the primary sources for its Concepts **in this run**, with WebFetch, and checks every claim against them;
- writes only `content/$stack/question-bank/challenge-<number>.json` for its own Challenges (Questions and Concepts), never another file;
- returns the three Question IDs for each Challenge, and the source URLs it read.

Done when every new Question has at least one Source accessed today (UTC) and every new Concept has a sibling.

## 5. Write the Challenge files

For each Day write `content/$stack/challenges/<number>.json` (zero-padded to three digits, `001.json`):

```json
{
  "schema_version": 1,
  "number": 1,
  "date": "2026-09-27",
  "questions": ["c001-q01", "c001-q02", "c001-q03"]
}
```

2-space indent, UTF-8, a final newline. Never edit or delete a Challenge whose Day is today or earlier: it is released and frozen. Only future Days are editable.

## 6. Check

```bash
uv run --project api content-check content/$stack
```

Fix every error and run it again. Done when it reports **no errors**, **no "clearly the longest" warning** for a Question you wrote (multiple choice or multiple select; for a Challenge Question it is blocking: rebalance the choices), no "Upcoming Challenge with a written Question" warning for a Challenge you wrote, and its line for the Stack says "Challenges written through <the last Day you wrote>". A Concept-repeat warning is fine only for a repeat you chose in step 3.

## 7. Report

End with:
- the Challenges written: number, Day, and each Question's ID and Concept;
- the check's "Challenges written through ..." line;
- the Concepts repeated, and why;
- every judgement call you made while nobody could be asked;
- anything the Admin should look at before committing.

Leave committing to the Admin.
