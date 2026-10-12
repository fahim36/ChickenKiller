# Voice mock interviews: agreed design

Status: accepted by the product owner on 11 October 2026, including final shared-understanding confirmation. Eight implementation tickets and their blocking edges were approved and published as GitHub issues #21–#28. Implementation and verification are tracked in [progress](mock-interview-progress.md). No production benchmark or deployment was performed; Whisper remains disabled under the documented gate decision.

## Purpose and first release

Offer guided spoken practice with little typing: hear a scenario, explain reasoning aloud, confirm the transcript, receive useful feedback, and optionally try again. English answers with varied accents are in scope; Bengali and Bengali-English mixed answers come later.

Launch with 16 reviewed Interview Prompts, four per Stack. Each has a linked Concept and teaching Lesson, a reviewed rubric, common misconceptions, Sources and reviewed follow-up options. These are separate from the append-only Question Bank and legacy written Questions.

A normal session uses three distinct eligible Concepts and targets roughly ten minutes. Optional retries can extend it. Eligible topics come from Completed Lessons or already-played Daily Challenges, with Weak Concepts prioritized among those having reviewed prompts. Learners can choose eligible topics manually. Use a shorter one- or two-topic session if necessary; if none qualify, explain why and link to an appropriate Lesson. Do not fill sessions with unstudied topics.

## Answer flow

1. Show and speak one reviewed scenario using device speech; visible text is always available. Do not call Gemini speech generation. If speech playback or microphone access is unavailable, keep text and optional typed responses usable.
2. Record the main response for at most 90 seconds. A turn permits at most one replacement recording. Visible recording controls, stop, skip and processing state should make the microphone behavior clear.
3. Transcribe using the selected available path. Show the transcript for explicit confirmation or correction before requesting feedback. A recognition error is not evidence of poor technical understanding.
4. Request rubric-grounded Gemini feedback once for the confirmed response. Assess correctness, reasoning, trade-offs and explanation structure using response evidence. Explain uncertainty and avoid grading accent or producing a readiness percentage.
5. The same feedback response may select an ID from the reviewed follow-up options. Validate the ID and keep the follow-up relevant to the same scenario. Allow at most one follow-up response, up to 45 seconds.
6. Allow one optional practice retry of the main scenario, up to 60 seconds. It receives the same evidence-based assessment and may show whether the previously identified omission was addressed.
7. Finish with concise improvement suggestions and relevant Lesson links. Interview Feedback never changes Quiz correctness, unlocking, Streaks or Weak Concept calculations.

A skipped, untranscribed, pending or failed response is not an incorrect answer. If the learner declines AI processing, lacks an enabled key, reaches quota or exhausts the app budget, reviewed rubric self-review remains available. Self-review can use temporary audio playback while the recording still exists; AI feedback can be retried later within the retained-response lifetime and remaining session budget.

## Transcription and benchmark gate

Prefer server-side faster-whisper only after a benchmark validates it. Open-source Whisper has no transcription API fee, but server CPU, memory, storage and maintenance are real costs. Current VPS spare capacity and representative transcription quality are unverified.

The accepted gate requires acceptable English technical-term transcription across varied accents, spare server capacity, and a target of no more than 30 seconds to transcribe a 90-second answer (updated by the user on 12 October 2026). Accuracy takes priority over speed: review technical terms, negations and meaning-changing mistakes against reference transcripts; transcript confirmation does not substitute for passing the quality gate. Test representative quiet/noisy recordings; record results and hardware rather than relying on third-party benchmark numbers. Use one worker with a bounded queue and protect the existing app under concurrent load. Document the model and resource limits chosen from those results.

If Whisper fails the benchmark or its bounded path is unavailable, use recorded-audio transcription through the learner's own Gemini key only with processing consent and remaining budget. Keep the approved Whisper path for ordinary corrections when available; do not silently switch providers for a correction. Browser Whisper is deferred because model downloads and device-dependent delays add launch complexity.

## Gemini free-quota policy

Use only the learner's own Gemini Developer API key, explicitly enabled for interview use. Reuse secure encrypted-key handling where suitable, but use a separate interview provider policy: no Admin-key, CLI or other-provider fallback. Update the existing grading-only key-use description.

Require learner confirmation that the key belongs to a Free Tier project with billing disabled. Clearly disclose that this is attestation, not machine verification or a zero-billing guarantee. Reviewed Google documentation does not establish a free-only inference flag or reliable billing-tier detection from an API key alone.

Before sending any audio or transcript, obtain explicit consent explaining Gemini free-tier processing and product-improvement data use. Declining preserves self-review. Google processing/retention terms are separate from this app's deletion rules.

Use a currently verified free-tier-capable audio/text model. Actual project quotas vary and may be shared with the learner's other applications. Do not promise a universal number of free interviews or treat another key on the same project as fresh quota.

- Maximum 18 Gemini requests per session, including failures, transcription calls, corrections and later retries.
- One Gemini request at a time per learner; budget reservations and duplicate-submission handling must prevent accidental repeat spending.
- No automatic retry after quota exhaustion, hidden paid upgrade or fallback key. Preserve the pending operation and offer self-review.
- A maximum-size session has nine evaluated responses: three main, three follow-up and three practice retries. Whisper ordinarily needs at most nine Gemini feedback requests; Gemini audio may add nine transcription calls. Replacement recordings or failures can consume the remaining budget before all feedback is available.
- Reuse a confirmed transcript for feedback retries. Use short structured rubric context and bounded feedback output; do not send full unrelated history.

## Privacy and retention

Transcripts and feedback are private learner history retained for 30 days, with learner deletion available earlier. Restrict response access to the owner; operational logs and aggregate diagnostics should not contain API keys, audio or response text.

Delete audio after transcript confirmation. Audio awaiting or failing transcription expires after at most 24 hours. Preserve it for temporary playback/retry within that period, and show its expiration. If it expires without a transcript, do not imply the answer can still be recovered: offer rerecording or self-review instead. Expiration/deletion cleanup and error paths need verification, including cancelled and abandoned sessions.

The interface must distinguish pending feedback, reviewed self-review and completed AI feedback. Missing AI feedback does not erase a confirmed transcript. Local audio/text deletion does not claim to erase material already processed by Google under its own terms.

## Domain boundaries and repository fit

- Reviewed Interview Prompts, rubrics and follow-up options stay in the existing reviewed content pipeline.
- Runtime Gemini produces private feedback and selects reviewed follow-ups; it does not generate or change canonical Questions or Syllabuses.
- Use separate session/response/feedback evidence rather than forcing spoken practice into existing quiz Answer correctness or legacy Grader interfaces.
- Authentication and Active Stack ownership are reusable. Dedicated bounded audio transport, temporary storage, cleanup and worker operations are new work.
- Existing ingress has a 5 MB body limit and the API is private behind the web service. Validate supported recording formats and size/duration limits; do not assume current JSON transport handles audio.

## Completion and verification

The product owner confirmed that this coherent design matches their intent on 11 October 2026. Prepare the specification/tickets or implement when explicitly requested.

Required verification covers eligibility and shorter sessions, reviewed follow-up selection, transcript correction, request counting/concurrency/idempotency, quota/provider failures, no fallback key, consent refusal, microphone/recording failures, English accent/technical-term transcription, benchmark resource/latency results, learner ownership, deletion/expiry and separation from quiz progression. Run representative feedback evaluations against reviewed rubrics; report uncertainty and observed quality.

Benchmark failure selects Gemini audio rather than blocking the whole feature. End-to-end rollout must be reviewed and tested; design confirmation does not itself authorize production deployment or merging.

## References and decisions

- [Implementation order, ticket paths and commands](mock-interview-implementation-order.md)
- [Gemini provider research](mock-interview-provider-research.md)
- [Whisper transcription research](mock-interview-transcription-research.md)
- [ADR 0010: separate interview evidence](adr/0010-interview-feedback-is-separate-practice-evidence.md)
- [ADR 0011: learner free-tier keys](adr/0011-mock-interviews-use-learner-free-tier-gemini-keys.md)
- [ADR 0012: reviewed prompts and private feedback](adr/0012-reviewed-interview-prompts-with-private-ai-feedback.md)
- Canonical glossary terms: Mock Interview, Interview Prompt and Interview Feedback in CONTEXT.md.

Design tree: objective, quota failure, key ownership, evidence boundary, session size, transcription, billing confirmation, speech output, turn limits, transcript correction, retention, content coverage, feedback policy, request budgets, topic eligibility, provider consent, benchmark gate and launch language are all settled. Final shared-understanding confirmation is complete.
