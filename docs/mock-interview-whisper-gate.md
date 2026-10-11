# Whisper gate: disabled, Gemini audio selected

Decision date: 11 October 2026. Ticket #25 permits an infeasible or unverified gate to complete with Whisper disabled. This is that outcome, not a successful benchmark.

## Evidence available

Repository inventory found no representative audio corpus, permission records or reviewed reference transcripts. Generated silence/container fixtures in `api/tests/test_interview_audio.py` check decoding and duration only; they provide no recognition-quality evidence.

The development machine reports an Intel Core i5-1235U (10 cores, 12 logical processors). It runs Windows and existing Docker development services. Its momentary free memory and laptop performance cannot establish spare resources on the shared deployment VPS. No production hardware inspection or production load test was performed. `deploy/vps/docker-compose.yml` gives Postgres, API and web one host and declares no transcription worker, resource reservation or queue. Candidate packages/models are not installed or downloaded.

Candidate for a future isolated benchmark: faster-whisper `small.en`, CPU INT8, one worker. This candidate is unverified; model/runtime versions must be pinned in the benchmark record before use. Published third-party numbers in [transcription research](mock-interview-transcription-research.md) are not measurements of this app.

| Required evidence | Result |
| --- | --- |
| Consented English recordings across accents, all four Stacks, quiet/noisy conditions | Unavailable |
| Reviewed reference transcripts, technical-term and meaning-changing error review | Not measured |
| Target: 90-second answer transcribed in at most 20 seconds | Not measured |
| Warm/cold latency, peak RAM/CPU and spare deployment capacity | Not measured |
| Existing API/web responsiveness with one worker and bounded queue load | Not measured |
| Recognition hallucinations/silence and correction burden | Not measured |

## Runtime behavior

Whisper is disabled without an environment override or worker installation. `GET /me/interview-transcription` exposes the selected `gemini_audio` path and unverified gate to authenticated learners; it contains no audio, transcript or credentials. The recorder explains this path and its shared request cost. Every Gemini attempt still requires the owner's enabled key, free-project attestation and processing consent, reserves one of 18 attempts and acquires the same owner-level in-flight lock. No automatic provider fallback or quota retry is introduced. Typed/manual confirmed transcripts and reviewed self-review remain usable without a key. No paid provider is configured.

The existing confirmed-transcript flow is the selected end-to-end path. Decoding tests cover WAV/WebM/Ogg/MP4, actual duration and bytes. Integration tests cover ownership, expiry, repeated upload/operation IDs, replacement bounds and deletion during a provider call; budget and overlap tests cover the shared owner lock. With no Whisper worker, there are no Whisper jobs, queue or overload claims. Gemini unavailability is handled explicitly; it never silently launches another transcription provider.

## Requirements before enabling later

Use an isolated environment representative of the target host; obtain consented recordings and expected transcripts with provenance. Record pinned faster-whisper/CTranslate2/model revisions and artifact checksums, candidate quantization, hardware and process limits. Keep model files in a persistent read-only model directory, outside learner storage. Installation must be a separate worker image, not an API request worker.

Measure cold and warm latency for 30/45/60/90-second clips, technical-term and meaning-changing errors by accent/noise/Stack, silence hallucinations, peak RAM/CPU, queue pressure and API/web responsiveness under bounded load. Report individual failures and representative quality; synthetic-only clips cannot pass. Enabling requires acceptable reviewed quality, spare app capacity and the 20-second target. Set concrete CPU/RAM limits from those measurements, one worker, a bounded queue and bounded job deadline; do not guess production limits from laptop measurements.

Only a passing reviewed record justifies worker integration. Jobs must carry owner/session/recording identity, enforce cancellation and expiry, and recheck stored state before writing a result; never recreate a deleted clip or overwrite confirmed text. Then keep Whisper pinned while available; an explicit consented Gemini action may handle unavailable capacity, never a hidden request. Diagnostics may record counts, timings and error categories, never audio/text/key payloads.

Rollback/disable must stop admissions and worker jobs, remove pending job audio, invalidate late results, and expose the Gemini/self-review path. Today's rollback is already that disabled state: no worker, models, queue or hidden inference costs exist. Production deployment and load testing remain outside this implementation's authorization.
