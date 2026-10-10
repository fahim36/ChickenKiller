# 04: Let Learners submit and track private Question Reports

**What to build:** After answering an active Question, a Learner can report a defect, edit an Open report and inspect their own report status.

**Blocked by:** None (can start immediately).

**Status:** draft (proposed ready-for-agent; not published to GitHub)

- [ ] Support one required category: wrong answer, ambiguous wording, outdated claim or broken Source, plus an optional note.
- [ ] Expose reporting from answered Lesson Quiz, Challenge, Retake and Review views; verify report eligibility on the server and show retirement reasons instead of inviting reports on retired Questions.
- [ ] Persist at most one unresolved report per Learner and Question, including concurrent submissions; only Open reports are editable.
- [ ] Provide an accessible submission/editing flow and a private view of the reporter's own reports and statuses.
- [ ] Enforce reporter/Admin access in reads and mutations; guessed identifiers cannot reveal another Learner's report.
- [ ] Filing or editing reports changes no score, Streak, Missed Question or completion; this does not implement legacy Disputes.
- [ ] API/UI tests cover categories, validation, concurrent deduplication, after-answer eligibility, retirement and authorization.

