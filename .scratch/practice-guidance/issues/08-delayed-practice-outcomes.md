# 08: Measure delayed variant performance after targeted practice

**What to build:** An Admin can inspect whether Learners answer distinct, previously unrecorded variants correctly 7–14 Days after targeted practice, with denominators and limitations.

**Blocked by:** 03: Recommend one useful Next Action on Home.

**Status:** draft (proposed ready-for-agent; not published to GitHub)

- [ ] Record recommendation uptake and the Concept actually practised through the targeted Review action; a click alone is not completed practice.
- [ ] Attribute a later answer to the most recent completed targeted practice of the same Learner/Stack/Concept that precedes it; include it only when that practice is 7–14 UTC Days earlier.
- [ ] Count each qualifying Question once per Learner/Stack using its first recorded, actually answered, graded outcome; exclude retired Questions, repeats and waiver events.
- [ ] Expose an Admin-only summary of accuracy, qualifying answers, Learners and Concepts plus recommendation uptake and Retake completion; show an honest empty state.
- [ ] State that unrecorded replays mean first recorded answer is not proven first exposure; avoid mastery or interview-readiness claims.
- [ ] Show the descriptive measure with denominators rather than implying causality or a validated optimal delay; do not log keys or answer text in general analytics.
- [ ] Fake-clock/API/UI checks cover Day 7/14 boundaries, multiple practice sessions, wrong-Concept attribution, repeated answers, retirement, privacy and sparse samples.

