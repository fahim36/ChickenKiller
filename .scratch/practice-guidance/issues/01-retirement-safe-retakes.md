# 01: Prevent retired Questions from blocking Lesson completion

**What to build:** A Learner never has to answer retired content to finish an already-passed Lesson Quiz, and can see why a pending Retake was replaced or waived.

**Blocked by:** None (can start immediately).

**Status:** draft (proposed ready-for-agent; not published to GitHub)

- [ ] Retirement of the original missed Question removes its pending Retake requirement with a recorded retirement reason.
- [ ] A retired waiting Retake is replaced with an active sibling; if none exists, waive only that requirement with a recorded content-gap reason, without falling back to the original Question.
- [ ] Retake retrieval and submission both enforce the rule, including retirement after a Question was displayed; repeated requests are safe.
- [ ] A Lesson completes only if its Quiz passed and every other Retake is resolved; waivers generate no correct Answer evidence.
- [ ] Show replacement/waiver reasons in the learning flow; preserve Completed Lessons and finished Challenge scores.
- [ ] API, rule and UI checks cover original retirement, waiting-sibling retirement, no sibling, concurrent/repeated requests and failed-Quiz protection. Follow ADR-0009.

