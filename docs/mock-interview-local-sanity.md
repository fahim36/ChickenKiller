# Local mock-interview sanity check

Run: 11–12 October 2026, Asia/Dhaka, branch `codex/mock-interviews`.

## Environment and boundaries

A consistent PostgreSQL custom-format snapshot was streamed from the production database over verified SSH. Only the local `jobhunt-db-1` database `learning` was dropped and restored. Local migrations advanced the copy from 0022 to 0026, then current content imported successfully, including 16 Interview Prompts and 32 Question variants. Production was not changed or deployed. The snapshot is excluded from Git and restricted to the local account.

A dedicated Clerk development account, `mock-sanity-20261011+clerk_test@example.com`, signed in through the actual local app with the development email code. It is a Learner, not an Admin. Onboarding selected Full Stack .NET Developer. Four Completed Lessons were seeded only for this dummy learner after verifying that the fresh learner had no eligible interview topics. Copied learners and their keys were not used for inference. The designated test Gemini key was saved through Settings and enabled through interview-specific consent controls.

The web app ran with `next dev --webpack --hostname localhost`, the actual API on localhost:8000, and the restored database. Binding Next to 127.0.0.1 caused Clerk's development rewrite to localhost to fail; matching the localhost binding resolved it. No authentication bypass was introduced. A separate Backend API token probe was refused by the application's normal origin checks.

## Actual UI and provider checks

- Real Clerk sign-in, onboarding and interview navigation passed.
- A fresh learner saw no interview start control and received a teaching Lesson link.
- Dummy-only studied-topic fixtures enabled manual topic choice and session creation.
- The main confirmed response was saved; real Gemini feedback returned four dimensions, exact evidence quotes and a reviewed follow-up.
- The reviewed follow-up opened with a 45-second audio limit. Generated device speech was inserted through the production upload/decoding policy as a local fixture, rather than recording ambient microphone content. Authenticated playback loaded its native controls.
- Real Gemini audio transcription returned the technical speech, including concurrency, coroutine, CSRF/CORS, JSON schema and untrusted-data terms. The learner edited and confirmed the transcript through the actual UI. Raw audio disappeared from the interface and database.
- A follow-up assessment and one explicit manual retry both returned `invalid_feedback`. The confirmed text and reviewed rubric remained available; each failed attempt was charged. No automatic retry occurred. One separate live diagnostic of the same synthetic response subsequently validated successfully, so model-output reliability remains a finding rather than a demonstrated deterministic application defect.
- The optional main retry opened with its 60-second limit and showed the original answer for comparison without claiming improvement. A deliberately incorrect answer was used to test real misconception feedback.

The visible session attempt count did not refresh immediately after transcription; it updated after transcript confirmation. Server accounting was correct. The sanity fix reloads owner-only session state after transcription, preserving the editable transcript and specific failure status. It suppresses late callbacks after leaving a turn and replaces the visible session only if its identity still matches. Focused tests cover the updated counter before confirmation and leaving a turn during transcription.

## Focused automated verification

39 API tests passed across self-review, voice, feedback, guided turns, resume and release/privacy scenarios. Fourteen frontend tests passed across five files covering the practice interface, voice controls, guided options, feedback and consent settings. These deterministic tests include failures and budget/privacy cases; they do not measure real model accuracy.

The copied database had 111 Quiz Answer rows before practice and after transcript confirmation. Interview work added no Quiz Answer evidence.

## Local Whisper measurements

Pinned faster-whisper 1.2.1, CTranslate2 4.8.2, PyAV 16.0.1, CPU INT8, four threads, one sequential worker on an Intel Core i5-1235U Windows laptop. PyAV 19.0.1 broke this runtime's `metadata_errors` decoder argument; the compatible decoder pin resolved it. The benchmark is isolated from the application environment.

Six speech cases and one silence case were run for each model: two synthetic device voices (Microsoft Heera and Zira), quiet audio, deterministic added noise and repeated/truncated 90-second audio. Model revisions and checksums, generated reference text, observed transcripts and timings are in [the measurements](mock-interview-whisper-local-benchmark.json).

An additional seven-case base.en run supplied a short technical-vocabulary hint, not the expected answer. This improved several spellings but still produced “quarantine scope” and corrupted CORS in a repeated clip. Silence remained empty. This is 21 local cases total, not a representative human-speech benchmark.

| Model | 90-second transcription times | Observed RSS after loading | Model load, excluding download |
| --- | --- | --- | --- |
| small.en | 25.77 / 26.23 seconds | 607 MiB | 2.13 seconds |
| base.en | 13.88 / 10.94 seconds | 501 MiB | 0.92 seconds |

Both models returned empty text for ten seconds of silence with VAD enabled. Short 39–45-second clips took about 12 seconds with small.en and 4–5 seconds with base.en.

Quality findings: small.en changed “untrusted data” to “untested data” on the Heera voice. Noise confused “non-idempotent” and “conflates.” Base.en sometimes changed “coroutine” to “quarantine,” corrupted JSON/CSRF/CORS spelling, and changed “non-idempotent” to “known idempotent” in a repeated sample. Substring term-presence checks in the JSON are diagnostics, not semantic correctness scores; an idempotent substring alone cannot verify negation.

**Whisper remains disabled.** The user revised the target to 30 seconds on 12 October 2026, prioritizing output quality. Small.en meets that revised timing target on the tested local clips (approximately 26 seconds); base.en is faster, but both have material technical-term errors. Synthetic voices are not representative human accent validation; this Windows laptop is not the shared ARM production VPS. No production capacity or queue load test ran. Actual microphone capture, physical iOS/Safari, human-accent quality and installed-screen-reader experience remain outside these live UI measurements. Transcript confirmation and self-review remain necessary, and do not substitute for passing the accuracy gate.

## Completion record

The recommended session contained three distinct studied scenarios. All three were skipped explicitly and remained saved as “Skipped — no assessment” after a browser reload. The earlier guided session retained its three responses and five charged operations: two completed assessments, one completed transcription, and two rejected feedback attempts. The incorrect retry received feedback identifying its distributed-lock and automatic-merge misconceptions.

Changing only the dummy learner's Active Stack to Android made the practiced .NET Stack inactive. Its original responses, reviewed rubrics and saved feedback still opened; new practice was refused as `inactive_stack`. The ordinary Stack form requires at least one selected Stack, so zero-Active-Stack history remains covered by the existing automated tests rather than this UI run.

Both disposable sessions were deleted through the actual UI and stayed absent after reload. Database verification found zero dummy sessions, zero dummy operations, and unchanged 111 Quiz Answer rows. The designated test key was removed through Settings; no dummy key remains. No copied learner was changed by these practice checks.

Live inference used six actual requests in total, including one explicitly separate diagnostic outside the app ledger; no automatic inference retry was made. Gemini audio and two assessments succeeded, while two follow-up assessments were rejected. This record does not establish universal feedback quality: strict validation and self-review remain necessary. Whisper remains disabled. Representative human-accent, deployment-capacity and physical-device checks remain unmeasured rollout qualifications.

The local Next development server completed these remaining checks. Production-mode restart was previously rejected by automatic approval review; development mode provided a successful authorized testing path. Final build, regression and review results are recorded in the progress log before the authorized main push.
