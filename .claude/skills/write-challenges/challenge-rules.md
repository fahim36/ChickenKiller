# Challenge Question rules

How to write the Questions of a Daily Challenge. They are ordinary Questions of the Stack's Question Bank, so [question-bank-rules.md](../update-syllabus/question-bank-rules.md) applies in full: the bank is append-only, read it before writing, and its "Each Question", "Accuracy" and "Permanent IDs" rules hold. This file only says what is different for a Challenge. Where the two disagree, this file wins for Challenge Questions.

## What a Challenge is

Three Questions for one UTC Day, the same for every Learner: **two multiple choice, then one multiple select**, in that order, each on a **different Concept**. Never written: written Questions are legacy ([ADR-0008](../../../docs/adr/0008-multiple-select-replaces-written-questions.md)), and the check refuses a new one, and an Upcoming Challenge that isn't two multiple choice then one multiple select. Released Challenges keep the written Questions they were released with. Only a Learner's first try is scored, and the Explanation and Sources show right after each answer. So every Question must stand alone: a Learner may meet it with no Lesson studied.

## Where the Questions go

- One bank file per Challenge: `content/<stack>/question-bank/challenge-<number>.json`, such as `challenge-001.json`, with the Concepts it declares and its Questions.
- **Question IDs** for a Question with no Lesson (`lesson: null`), the ID scheme this command gives it: `c<number>-q01`, `-q02`, ... (`c001-q01`), `<number>` being the Challenge it was written for, zero-padded to three digits. The three a Challenge uses come first, in its order; siblings follow. A Question tagged to a Lesson takes that Lesson's scheme instead (`<lesson-id>-qNN`, see question-bank-rules.md), in the same file.
- **Concept IDs**: `c<number>-<short-slug>` (`c001-tool-result-errors`), for a new Concept first used in that Challenge.
- Check an ID is unused before you mint it: `grep -rl '"<id>"' content/<stack>/`.

## Size and mix

- Each new Concept needs **at least 2 Questions that aren't retired** (the check refuses fewer), so a Missed Question can be re-tested with a sibling. The Challenge uses one; write **one spare sibling** per new Concept in the same file, not used by any Challenge. The sibling tests the same idea from another angle, and may be the other type (multiple choice or multiple select, never written).
- So a Challenge on three new Concepts adds six Questions to the bank. Size and mix rules for a Lesson's bank (8–12 Questions, a Lesson Quiz's mix) don't apply.
- A Challenge may use an existing Question of the bank instead of a new one only if no Challenge has used it and it isn't retired. Say so in the report.

## Lesson and Materials

- `lesson` is the Lesson of the newest Syllabus whose topics the Question tests, or `null` when it fits none. Prefer `null` for a Challenge's three Questions, so they are not drawn for a Lesson Quiz a Learner may already have met them in; tag the spare siblings to a Lesson when one fits.
- `materials`: 0–3 Material IDs from the newest `syllabus.json`. None fits is fine: Sources carry the checking. Don't add Materials to the Syllabus: that is a Syllabus Update's job.

## Difficulty and length

- A Challenge is a short daily game: about 5 minutes for all three. Prompts are at most 3 sentences, or a short code block plus one sentence.
- Aim at what an interviewer for the role would ask a mid-level candidate: a decision, a failure mode, a trade-off, or behaviour you'd only know from the docs. Not trivia (version numbers, dates, who said what).
- **Choices are balanced.** The four choices are about the same length, and the correct one is **never the longest** (nor the only one with a qualifier like "usually" or "only when"). Count the characters: if the correct choice is the longest, make a wrong one at least as long. For a Challenge Question the content check's "clearly the longest" warning is **blocking**: a run is not done while one names a Question it wrote.
- **Multiple select**: 4–6 choices (5 is usual), 2–3 of them correct, the prompt ending "Select all that apply." Marked all or nothing, so each choice is clearly true or clearly false by the Sources. The correct choices are **never all the longest**: at least one wrong choice is as long as the shortest correct one. Its "the correct choices (…) are clearly the longest" warning is **blocking** too.

## Sources

- Fetch each Source with WebFetch in this run, and set `accessed` to today's UTC date (`date -u +%Y-%m-%d`). A Source from memory, or from an earlier run, is refused by the check.
- The `claim` is the exact fact the Question's answer relies on, in your words. Check the keyed answer (every correct choice, for multiple select) against it, and each wrong choice too: a wrong choice must be wrong by the source, not only by opinion.

## Upcoming Challenges with a written Question

Upcoming Challenges committed before ADR-0008 may still end with a written Question. The check warns about each ("an Upcoming Challenge with a written Question, committed before written Questions became legacy (ADR-0008): rewrite it as 2 multiple-choice Questions, then 1 multiple-select, before its Day"), and refuses it outright once its written Question is retired. Rewrite each one you are asked to (or that this run's Days overlap): keep its two multiple-choice Questions, and replace the written one with the multiple-select Question that replaced it (`replaced_by`) or a new multiple-select Question on the same Concept. Only Upcoming Challenges can be rewritten: never touch one whose Day is today or earlier.
