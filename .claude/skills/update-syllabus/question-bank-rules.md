# Question Bank rules

How to write one Lesson's Questions, in the Stack's Question Bank: `content/<stack>/question-bank/<lesson-id>.json` (the bank is the Stack's, not a version's; files only group Questions, and each Question names its Lesson in `lesson`). Every agent that writes a bank follows these rules, whether it runs `/update-syllabus` itself or is one of its sub-agents.

The format is `content/schema/question-bank.schema.json`; the terms (Concept, Explanation, Model Answer, Retake, Lesson Quiz) are in `CONTEXT.md`. Write JSON with 2-space indent, UTF-8, and a final newline. Match the tone of the existing banks, such as `content/agentic-ai-engineer/question-bank/w01-l01.json`: plain English, short sentences, code in backticks.

## What a bank covers

The Lesson's `topics` and `exercise` in `syllabus.json`, and nothing beyond them. A Learner who studied the Lesson's Materials can answer every Question.

## Size and mix

- **8–12 Questions** over **3–6 Concepts**.
- **Every Concept has at least 2 Questions**, so a Retake always has a sibling to ask.
- **At least 6 multiple choice and at least 3 written.** A Lesson Quiz draws 4 multiple choice and 2 written; the rest are spares for Retakes and Review Rounds.
- **At least 4 Concepts have a multiple-choice Question**, so a Lesson Quiz can cover four different Concepts.

## Each Question

- **Concept**: the one idea it tests. A Concept's `name` is a short phrase, such as "Mutable default arguments".
- **Multiple choice**: 4 choices, `a` to `d`, exactly one correct. Wrong choices are plausible: each is a real misconception, and about as long as the right one. Spread the correct letter across the bank. No "all of the above" or "none of the above".
- **Written**: asks the Learner to explain, compare or decide. The Model Answer has a one- or two-sentence `summary` and 2–5 `key_points`. Each key point is one claim a grader can find, or not find, in an answer.
- **Explanation**: why the correct answer is correct and why the tempting wrong answer is wrong. It stands alone: the Learner reads it right after missing the Question.
- **Materials**: 1–3 Material IDs from the newest version's `syllabus.json`, pointing at the pages where the answer can be checked. Prefer the official docs page for the exact feature.
- **Lesson**: `lesson` is the Lesson's ID.
- **Sources**: at least one `{url, title, publisher, accessed, claim}` for every Question: the primary source fetched in this run, the UTC date you fetched it (`YYYY-MM-DD`), and the claim the Question relies on. The content check refuses a new Question whose Sources weren't accessed today or yesterday (UTC).

## Accuracy

- **Every factual claim is checked against a primary source fetched in this run**: official docs, specifications, PEPs and RFCs, papers, vendor docs, release notes. Blogs, forums and tutorials are leads to follow to the primary source, never the source itself.
- A fact that depends on a version says so ("Python 3.12+", "LangGraph 1.x").
- Work each code example through by hand. A Question whose answer depends on untested code behaviour is wrong until proven right.

## Permanent IDs

- **Questions**: `<lesson-id>-q01`, `-q02`, ... in file order.
- **Concepts**: `<lesson-id>-<short-slug>`, such as `w02-l01-protocol-structural-typing`. The Lesson prefix keeps Concept IDs unique when several agents write banks at once.
- **Revising an existing bank**: a committed Question is never edited or deleted (ADR-0004). To fix or replace one, retire it (`retired: {reason, replaced_by}`) and add a new Question with a new ID. A Concept's `name` may be reworded.
- **A new ID is never one used before**: number new Questions after the highest number this Lesson has used in any version (`grep -rh '"<lesson-id>-q' content/<stack>/`).

## New Materials

When a Question needs a Material that isn't in `syllabus.json`, pick the official page and describe it as `{id, title, url, type, subject}`:
- `url` is `https://` and loads;
- `type` is one of `book`, `docs`, `free`, `paid`, `paper`, `platform`, `tool`, `video`;
- `id` is a slug of the title, and not an ID already used anywhere in the Stack's versions.

Check first whether the Syllabus already has a Material with that URL, and reuse its ID if so.

## Done when

`uv run --project api content-check content/<stack>` reports no error in this bank's file. An error that names a Material you proposed but haven't added to `syllabus.json` yet is the one exception: the Syllabus Update adds it.
