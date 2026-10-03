# Multiple-select Questions replace written ones

This amends ADR-0003, ADR-0006 and ADR-0007.

A new Question is multiple choice or **multiple select** ("select all that apply": 4–6 choices, at least 2 correct and at least 1 wrong), never written. A multiple-select answer is the set of choices ticked, and it is correct only when that set is exactly the correct one: all or nothing, with no partial credit and no grading call. A Lesson Quiz is four multiple choice and two multiple select; a Daily Challenge is two multiple choice, then one multiple select. We chose this over keeping written answers graded by an LLM because grading was the app's one slow, costly and fallible step: a written answer took seconds to grade, needed the Claude Code CLI or an LLM key, could fail ("ungraded", resubmit), and a Learner could dispute its verdict. A multiple-select Question still tests more than one fact at a time, is marked at once and the same way every time, and can't fail to grade.

## Consequences

- Written Questions are legacy. The append-only bank (ADR-0004) keeps every committed one, and released Daily Challenges are frozen, so Agentic AI Engineer #1 to #7 keep their written Questions for good, and the Archive replays them. Grading (ADR-0006, ADR-0007) stays for those: written answers are still graded, and a Learner's own key still works.
- Every written Question in the bank is to be retired, `replaced_by` a multiple-select Question on the same Concept. Until a Lesson's are, its written Questions fill the Lesson Quiz's multiple-select slots when it has too few multiple-select ones.
- The content check refuses a new written Question; it counts written Questions toward a Lesson's two multiple-select ones; and it holds an Upcoming Challenge to two multiple choice, then one multiple select. A released Challenge keeps the mix it was released with. An Upcoming Challenge committed with a written Question and unchanged since is only a warning, until it is rewritten or its written Question is retired (an Upcoming Challenge can't use a Retired Question).
- A new multiple-select Question whose correct choices are each longer than every wrong one is a warning, like the "clearly the longest" warning for multiple choice.
- The MCP connector refuses written Questions in drafts, and a Challenge draft that isn't two multiple choice then one multiple select. A new Stack's Lessons need four multiple choice and two multiple select.
- A multiple-select Question is never ungraded, so its Result Card mark is always ✅ or ❌. Only a legacy written Question can show ⬜.
- `questions.answers` stores every correct choice ID of a multiple-select Question; a Learner's answer is stored in `answers.response` as the ticked IDs, sorted and comma-separated ("a,c").
