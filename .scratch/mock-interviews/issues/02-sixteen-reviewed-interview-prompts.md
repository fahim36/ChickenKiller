# 02: Publish 16 reviewed Interview Prompts across the four Stacks

**GitHub issue:** [#22](https://github.com/fahim36/ChickenKiller/issues/22)

**What to build:** Learners in all four Stacks can practise a useful set of distinct studied Concepts, and the Admin can inspect which reviewed interview topics are available.

**Blocked by:** 01 — Start a private Mock Interview with reviewed self-review.

**Status:** ready-for-agent (breakdown approved; blockers still gate implementation).

## Acceptance criteria

- [ ] Complete a total of 16 reviewed Interview Prompts, four per Stack, including ticket 01's four seeds. Prefer distinct high-value Concepts and preserve permanent existing content identifiers.
- [ ] Each prompt has a concrete technical scenario, Concept/teaching Lesson link, rubric, realistic misconceptions, primary Sources and relevant reviewed follow-up options. Follow-ups probe reasoning, failure cases or trade-offs within the taught topic.
- [ ] Rubrics distinguish correctness, reasoning, trade-offs and explanation structure; they do not assess accent or produce a readiness score. Review the claims, expected reasoning and follow-up options against fetched primary Sources.
- [ ] Validate reference integrity and reviewed follow-up IDs; import is repeatable and historical session content stays reproducible. Do not generate canonical content at runtime or write new written Questions.
- [ ] All 16 prompts appear in the imported eligible selection flow when their topics are studied. At least one completed-topics example per Stack demonstrates a three-distinct-Concept session and manual topic choice.
- [ ] Provide an Admin-only coverage view for reviewed Interview Prompts by Stack/Concept, including missing/unresolved teaching references, without exposing private learner responses. Reuse Content Health where appropriate without making it a prerequisite for the learner flow.
- [ ] Content/import/API/UI checks verify the full batch, coverage privacy and continued operation of ordinary Quiz/Review content. Document editorial review and intended coverage rather than claiming quality from counts alone.

## Scope

Canonical reviewed content and its discoverability only. The provider and audio tickets can proceed with the validated seed prompts; this batch is not a software dependency for them.
