# 02: Show Weak Concept evidence on each Stack page

**What to build:** A Learner can inspect each active Stack's Concept evidence, identify recent weaknesses and recovery, and open the relevant Lesson.

**Blocked by:** None (can start immediately).

**Status:** draft (proposed ready-for-agent; not published to GitHub)

- [ ] Trigger weakness after incorrect answered outcomes on two distinct active Questions in the current and preceding 29 UTC Days; repeated misses on one Question do not inflate the count.
- [ ] Recovery requires correct recorded answers strictly after the latest qualifying miss on three distinct UTC Days across at least two distinct active Questions; a new miss restarts recovery.
- [ ] Use actually answered recorded Lesson Quiz, Challenge, Retake and Review outcomes; exclude unanswered slots, ungraded results, replays and retired Questions.
- [ ] Rank weak Concepts by distinct recent missed Questions, then latest qualifying miss and stable Concept ID; show supporting counts/dates rather than mastery percentages.
- [ ] Distinguish insufficient evidence, expiration and recovery; deactivation hides guidance without losing history and reactivation recalculates current evidence.
- [ ] Serve only the signed-in Learner's evidence and provide accessible Stack-page evidence and Lesson links, including missing/removed Lesson handling.
- [ ] Fake-clock rule tests and API/UI checks cover UTC/window boundaries, repeated attempts, recovery resets, retirement and cross-Learner/Stack isolation.

