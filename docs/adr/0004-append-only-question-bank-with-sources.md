# The Question Bank is append-only and every Question has Sources

Each Stack has one Question Bank that only grows. A Question gets a permanent ID and is never edited or deleted; a wrong or out-of-date Question becomes a Retired Question with a reason and, optionally, the Question that replaces it. Every Question has at least one Source (URL, title, publisher, date accessed, and the claim it relies on), and all of its Sources must have been accessed in the run that wrote it. We chose this over editing or deleting Questions in place because Daily Challenges are shared and frozen once released: the Archive must show what Learners actually answered, and past results must stay tied to the Question they answered. Sources make every Question checkable and keep the Admin from citing from memory.

## Consequences

- A Syllabus Update no longer replaces the Question Bank. It can add Questions, retire them, or re-tag them to a different Lesson. The Syllabus itself (Weeks and Lessons) is still versioned and replaced.
- The content check rejects a Question with no Source, or with a Source not accessed in the current run.
- Before writing new Questions, the Claude Code command reads the whole Question Bank. The content check warns, but doesn't block, when a new Question repeats an existing Concept, so any repeat is deliberate.
- Retired Questions stay visible in the Archive, can't be answered, and are never drawn for Lesson Quizzes, Retakes or Review.
- The Admin writes Upcoming Challenges a few Days ahead. They can be edited until released; a Day with nothing written has no Challenge. The content check and an Admin page warn when fewer than three Days are written.
