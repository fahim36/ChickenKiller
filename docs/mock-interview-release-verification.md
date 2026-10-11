# Guided Mock Interview release verification

Branch: `codex/mock-interviews`. Reviewed content baseline: `e8d4b11`. Verification date: 11 October 2026. This record covers implementation and local checks; no production merge, deployment, production load test or live provider request was performed.

## Feature and test coverage

The release has 16 reviewed prompts, four distinct Concepts per Stack. `test_interview_coverage.py` imports all four current Stacks twice, verifies all 16 eligible topics after teaching Lessons, three distinct Concepts, manual choice and Admin content-only coverage. Earlier selection tests cover Weak Concepts, played Daily Challenges, shorter sessions and no eligible topic. Question Banks, Syllabuses and Challenges have no diff against the branch baseline.

`test_interview_release.py` exercises consented own-key setup, temporary recording/playback, mocked transcription, correction before assessment, raw-audio deletion, evidence quotes, the reviewed follow-up, optional retry, six charged requests, owner history/resume and deletion. Replayed operation IDs send nothing. Optional turns use server-derived 90/45/60-second limits and one replacement per turn. The API/guided tests cover nine responses, order, duplicate/recursive turns, shared 18-attempt exhaustion and no new Quiz Answer rows.

Failure tests cover microphone refusal, unavailable formats/voices/playback, decoding/size/duration, replacement and failed playback, unsupported uploads, owner-only access including Admin denial, consent refusal/withdrawal, missing/changed keys, quota, malformed provider envelopes/output, a bounded HTTP timeout, interrupted attempts, in-flight owner overlap, deletion/expiry and late results. Database errors may include private SQL parameters; the interview route boundary returns a generic storage error instead of exposing/logging the exception. New work rechecks eligibility and reviewed versions; history remains available for inactive Stacks, including with zero Active Stacks.

Whisper is **disabled, unverified**, as explicitly allowed by ticket 05. There are no worker jobs or queue to overload. [The gate record](mock-interview-whisper-gate.md) lists missing representative corpus and deployment measurements, requirements for later installation and the actual selected Gemini/self-review path. No benchmark passed and no unlimited-free allowance is claimed.

## Browser evidence

The reproducible local script is `web/scripts/interview-browser-smoke.mjs`. It starts an isolated headless Edge/Chromium profile, a synthetic microphone and the actual VoiceResponse/DeviceSpeech components with mocked Server Actions. It sends no credentials or provider requests. The fixture harness omits product styling and full site authentication; API tests separately verify those authorization boundaries.

[Saved browser measurements](mock-interview-browser-verification.json) show two successful modes: desktop 1280×900 and mobile viewport 390×844. Keyboard Enter started recording; native MediaRecorder produced WebM/Opus, playback loaded, the mocked transcript was corrected and confirmed, audio disappeared and microphone status returned to off. No horizontal overflow appeared in the controls harness. Recordings from the earlier lifecycle run decoded through the production normalization function to 26,924 and 25,004 WAV bytes; subsequent runs vary in recording length. These are synthetic format/lifecycle measurements, not accent/recognition-quality results.

The browser advertised WebM/Opus and MP4; Ogg support varies and is feature-detected. Independent FFmpeg tests exercise WebM/Ogg/fragmented MP4/WAV decoding. The browser accessibility tree exposes named Stop/Cancel recording buttons and the labelled transcript textbox in both viewports. React tests verify explicit labels, button controls, live microphone/processing status, transcript correction, typing/skip fallback, unavailable device speech and preservation of per-turn drafts. Private history reload/open/delete also works without Active Stacks.

Physical Android/iOS devices, Safari, an installed screen reader and varied-accent recordings were not available in this run. Do not infer those measurements from mobile emulation. Unsupported recording APIs/formats retain the typed/self-review path. Confirm target physical devices in an authorized staging smoke before making platform-specific support or transcription-accuracy claims.

## Reviewed feedback cases and limitations

| Reviewed response | Rubric interpretation | Verified contract |
| --- | --- | --- |
| “A lock in this process protects all replicas.” | Plausible misconception: process-local coordination does not cover all replicas. | Exact submitted evidence remains intact; reviewed follow-up membership is checked. |
| “A process-local lock does not protect other replicas.” | Negation matters; this acknowledges the distributed boundary but needs a concrete mechanism. | No negation removal/rewriting in provider context or accepted quote. |
| “I would lock it, but I cannot explain the competing update yet.” | Incomplete reasoning; ask for the actual interleaving and shared-store coordination. | Incomplete text is retained; uncertainty remains explicit. |
| “Use a token, not a taken, and compare the database version.” | Recognition correction restores the technical term before assessment. | Feedback uses the corrected confirmed text; it does not reuse raw recognition output. |

These four examples are reviewed against the seed concurrency rubric. Deterministic provider fixtures validate transport, evidence identity and structured-output rejection; they do **not** establish real Gemini reasoning accuracy. Fabricated quotes, repeated dimensions and unreviewed follow-up IDs are rejected. Exact quotation alone cannot establish whether an AI finding interprets negation or technical claims correctly. Accent quality, semantic grading accuracy and model variability remain unmeasured without permissioned recordings and explicitly consented live inference. No readiness percentage, accent grade or improvement claim is emitted.

## Reproducible checks

From `api`: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run content-schema --check`, and `uv run pytest -q`. API tests use a separate migrated PostgreSQL test database. Run only one pytest process against it at a time. The four-Stack integration imports committed content twice; migration checks rebuild the test schema.

From `web`: `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`. From the repository root: `uv run --project api content-check content --baseline e8d4b11 --today 2026-10-11`. Ordinary CI installs FFmpeg explicitly and uses deterministic provider mocks; no external inference or link checks are required.

For the optional browser smoke, run `node scripts/interview-browser-smoke.mjs` from `web`. Windows defaults to installed Edge; another Chromium binary can be supplied in `INTERVIEW_BROWSER`. Ports 4179 and 9228 must be free. A temporary isolated browser profile and local fixture server are created; both processes are closed at completion. Synthetic recordings, screenshots and a report are written under `.scratch/mock-interviews/browser-smoke`. No personal browser profile is used. Vite/React use the existing project dependencies.

Final suite counts, review fixes and branch pushes are recorded in [implementation progress](mock-interview-progress.md). See [operation guidance](mock-interview-operations.md) for installation and the separately authorized rollout checklist.
