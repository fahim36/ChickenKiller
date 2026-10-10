# 03: Recommend one useful Next Action on Home

**What to build:** After a Daily Challenge, a Learner sees one optional, actionable recommendation and up to three Weak Concepts across Active Stacks.

**Blocked by:** 01: Prevent retired Questions from blocking Lesson completion; 02: Show Weak Concept evidence on each Stack page.

**Status:** draft (proposed ready-for-agent; not published to GitHub)

- [ ] Choose oldest pending Retake first, then eligible due Review for the highest-ranked Weak Concept, then an Unlocked Lesson in the most recently practised Stack.
- [ ] If no Lessons remain, offer ordinary due Review; with no eligible activity, show completion and links to Materials/Milestones.
- [ ] Break remaining ties deterministically; Stacks with no recorded practice use stable ordering.
- [ ] A weak-Concept Review action opens practice for that Concept drawn only from the existing due queue, and submissions retain normal eligibility checks; do not expose a new non-due practice bypass.
- [ ] Show a reason, evidence and working links; preserve other activities, shared Daily Challenges, Streak rules and optional Review.
- [ ] Handle retirement-safe pending Retakes and sparse/empty evidence without dead recommendations.
- [ ] API/UI and integrated checks demonstrate ordering, tie handling, targeted due Review, fully completed Stacks and empty queues.

