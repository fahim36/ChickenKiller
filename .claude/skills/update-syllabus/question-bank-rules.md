# Question Bank rules

How to write a Question for a Stack's Question Bank, `content/<stack>/question-bank/*.json`. Every agent that writes Questions follows these rules: `/update-syllabus` and its sub-agents, and any other command that adds Questions (such as one writing Upcoming Challenges).

The format is `content/schema/question-bank.schema.json`, explained in `docs/content-format.md`; the terms (Question, Multiple select, Concept, Source, Material, Explanation, Retired Question, Retake, Lesson Quiz) are in `CONTEXT.md`. Write JSON with 2-space indent, UTF-8, and a final newline. Match the tone of the existing Questions, such as `content/agentic-ai-engineer/question-bank/w01-l01.json`: plain English, short sentences, code in backticks.

## The bank is append-only

The bank is the Stack's, not a Syllabus version's, and it only grows (`docs/adr/0004-*`). Against git `HEAD`:

- **A committed Question is never edited or deleted.** Its prompt, choices, answer, Explanation, Concept, Materials and Sources stay as they are.
- **To take one out of use, retire it**: add `"retired": {"reason": "...", "replaced_by": "<new question id>", "on": "YYYY-MM-DD"}`, with `on` today in UTC. `reason` says what is wrong or out of date, in a sentence. `replaced_by` is the new Question that tests the same Concept correctly, or `null` when nothing replaces it. A retirement is final.
- **To move one to another Lesson, re-tag it**: change only its `lesson`. Re-tag an existing Question rather than write a copy of it.
- **A Question written in this run** (not in `HEAD`) may still be edited or deleted until it is committed.

## Never write a written Question

Every new Question is `multiple_choice` or `multiple_select`. Written Questions (`"type": "written"`, with a `model_answer`) are legacy ([ADR-0008](../../../docs/adr/0008-multiple-select-replaces-written-questions.md)): the committed ones stay in the bank, but the content check refuses a new one (`a new Question is never written: written Questions are legacy (ADR-0008); write it as multiple_select`). Where you would have asked the Learner to explain, compare or decide, write a multiple-select Question instead.

To replace a live written Question, retire it with `replaced_by` naming a new multiple-select Question on **the same Concept** and tagged to the same Lesson, with the reason `"Written Questions are legacy (ADR-0008): replaced by a multiple-select Question on the same Concept."`. Never edit the written Question itself.

Files only group Questions (one file per Lesson, `<lesson-id>.json`, is usual). Add a new Question to the end of the file for its Lesson, or to the file your command names. A Question's Lesson is its `lesson` field, never its file.

## Before writing

Read every Question in the bank, retired ones included, and note the Concepts already tested (`concepts`, and each Question's `concept`). A new Question tests a new Concept unless it is deliberately a sibling on an existing one: a replacement for a Retired Question, or a Concept that needs more Questions for Retakes. The content check warns about each new Question on a Concept committed Questions already test; each such warning must be one you meant.

## Each Question

- **Concept**: the one idea it tests. A Concept's `name` is a short phrase, such as "Mutable default arguments". A new Concept is added to the file's `concepts`.
- **Lesson**: `lesson` is the ID of the Lesson that teaches it, in the Stack's newest Syllabus version, or `null` when no Lesson does. A Question tagged to a Lesson covers only that Lesson's `topics` and `exercise`: a Learner who studied the Lesson's Materials can answer it.
- **Multiple choice**: 4 choices, `a` to `d`, exactly one correct. Spread the correct letter across the bank. No "all of the above" or "none of the above".
  - **Every wrong choice is plausible**: each is a real misconception.
  - **The correct choice is never the longest by a margin.** Write the correct choice first, then make at least one wrong choice as long and as specific as it, with the same grammar and level of detail. Length must give nothing away; the content check warns about a new Question whose correct choice is more than 25% longer than every wrong one.
- **Multiple select** (`"type": "multiple_select"`): "select all that apply". It tests what a written Question used to: which of several claims, steps or options hold.
  - The `prompt` ends with "Select all that apply."
  - **4–6 choices**, `a` onwards, with unique IDs; `answers` lists the ID of **every** correct choice: **at least 2 correct and at least 1 wrong**. Aim for 2–3 correct out of 5. Vary which letters are correct across the bank.
  - It is marked **all or nothing**: right only when the Learner ticks exactly the correct choices. So every choice must be clearly true or clearly false by the Sources, with no "partly right" choice.
  - **Every wrong choice is plausible**, a real misconception, as for multiple choice. No "all of the above" or "none of the above".
  - **The correct choices are never all the longest.** Make at least one wrong choice as long as the shortest correct one. The content check warns about a new Question whose every correct choice is longer than every wrong one ("the correct choices (…) are clearly the longest").
- **Explanation**: why the correct answer is correct and why the tempting wrong answer is wrong. For multiple select, say why each correct choice holds and why each wrong one doesn't. It stands alone: the Learner reads it right after missing the Question.
- **Materials**: 1–3 Material IDs from the newest Syllabus version's `syllabus.json`, pointing at the pages where the answer can be checked. Prefer the official docs page for the exact feature.
- **Sources**: at least one, each with all five fields:
  - `url`: the `https://` primary source you fetched in this run;
  - `title`: the page's title;
  - `publisher`: who publishes it (such as "Python Software Foundation", "Anthropic");
  - `accessed`: the UTC date you fetched it, `YYYY-MM-DD`: today;
  - `claim`: the claim from that page the Question relies on, in a sentence.

  The content check refuses a new Question with a Source not accessed today or yesterday (UTC).

## Accuracy

- **Fetch every Source in this run and check the Question against it**: every correct choice, every wrong choice (each must be wrong by that source) and the Explanation. A Source you remember but didn't fetch is not a Source.
- Primary sources only: official docs, specifications, PEPs and RFCs, papers, vendor docs, release notes. Blogs, forums and tutorials are leads to follow to the primary source, never the source itself.
- A fact that depends on a version says so ("Python 3.12+", "LangGraph 1.x").
- Work each code example through by hand. A Question whose answer depends on untested code behaviour is wrong until proven right.

## A Lesson's Questions

When you write the Questions for a Lesson (a new Lesson, or one short of Questions), its live Questions (not retired), old and new together, end with:

- **at least 8**, over **3–6 Concepts**; a new Lesson gets **8–12**;
- **every Concept with at least 2**, so a Retake always has a sibling to ask;
- **at least 6 multiple choice and at least 3 multiple select**, and no written ones. A Lesson Quiz draws 4 multiple choice and 2 multiple select; the rest are spares for Retakes and Review;
- **at least 4 Concepts with a multiple-choice Question**, so a Lesson Quiz can cover four different Concepts.

The content check enforces the hard floor (8 live Questions, 4 multiple choice and 2 multiple select, 2 per Concept); the rest is the standard to write to. Until a Lesson's legacy written Questions are retired they still count toward the 2 multiple select (a Lesson Quiz asks them only when it runs out of multiple-select ones), but a Lesson you write Questions for ends with at least 3 live multiple-select Questions of its own.

## Permanent IDs

- **Questions**: `<lesson-id>-q01`, `-q02`, ... for a Question tagged to a Lesson. Number a new one after the highest number that prefix has ever used, retired Questions included: `grep -rho '"<lesson-id>-q[0-9]*"' content/<stack>/`. A Question with no Lesson takes the ID scheme of the command that writes it.
- **Concepts**: `<lesson-id>-<short-slug>`, such as `w02-l01-protocol-structural-typing`. The prefix keeps Concept IDs unique when several agents write at once.
- **A re-tagged Question keeps its ID**, even though its prefix now names another Lesson.
- **An ID is never reused**, not even one a Retired Question had.

## New Materials

When a Question needs a Material that isn't in the newest `syllabus.json`, pick the official page and describe it as `{id, title, url, type, subject}`:
- `url` is `https://` and loads;
- `type` is one of `book`, `docs`, `free`, `paid`, `paper`, `platform`, `tool`, `video`;
- `id` is a slug of the title, and not an ID already used anywhere in the Stack.

Check first whether the Syllabus already has a Material with that URL, and reuse its ID if so. Return new Materials to the command that started you; it adds them to the Syllabus.

## Done when

`uv run --project api content-check content/<stack>` reports no error and no "clearly the longest" warning (for a multiple-choice or a multiple-select Question) for the Questions you wrote, none of them is written, and every warning that one of them tests a Concept already tested is one you meant. An error that names a Material you proposed but that isn't in `syllabus.json` yet is the one exception: the command that started you adds it.
