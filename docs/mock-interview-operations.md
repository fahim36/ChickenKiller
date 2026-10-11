# Guided Mock Interview operations

This document describes a future authorized upgrade. Implementation testing did not deploy or merge the branch. Existing content-health changes are included in `codex/mock-interviews`; assess the whole branch when preparing a release.

## Install and upgrade

Use the existing PostgreSQL/API/web stack and existing Clerk authentication. Build the API image including FFmpeg; the normal `api/Dockerfile` installs it. No Whisper/PyTorch/model files, GPU, new inference service or paid provider is required. Follow the existing VPS upgrade procedure after separate authorization and a recoverable database backup.

From the API environment, run `uv run alembic upgrade head` and `uv run content-import ../content` against the intended deployment database. Repeat import is idempotent. Migrations 0023–0026 add separate private sessions, settings/attempt ledger, temporary recordings and optional turns; they do not convert Quiz evidence. The canonical prompt files and generated schema are committed under each Stack's `interviews` directory and `content/schema/interview-prompt.schema.json`. Confirm 16 prompts and four covered Concepts per Stack in `/admin/interview-coverage`; it does not expose private responses.

The built web service deliberately allows 5 MB Server Action bodies. Existing nginx ingress is 5 MB; do not lower an intermediate proxy below the bounded upload envelope without checking failure behavior. Browser files are limited to 3,000,000 bytes; server JSON base64 is limited to 4,000,000 characters, format headers are checked and FFmpeg validates real audio/duration. The decoder admits pipe input only, one thread, bounded decoded output and a 15-second process deadline. Audio is normalized for the provider, not accepted on MIME alone. Keep the private API loopback/internal; the browser calls authenticated web actions, never the private API/key directly. HTTPS is required for normal microphone use outside localhost.

`InterviewRecording.audio` is temporary private PostgreSQL binary storage. Maximum file size is 3 MB and one stored clip per open turn; a replacement removes its predecessor. Audio is unavailable at 24-hour expiry and removed by the next cleanup pass; confirmation, discard and owner deletion remove the corresponding rows immediately. Physical database page reclamation/backups follow PostgreSQL and operator retention, not secure-erasure promises. Configure backups/access consistently with private retention; app deletion does not erase previously submitted Google data.

## Cleanup and diagnostics

API lifespan starts an expiry task immediately and every 60 seconds. It deletes expired recordings and 30-day text sessions; cascades remove their operations/recordings. Read/write endpoints refuse expired material even before the next physical cleanup pass. API downtime may delay row deletion; run cleanup before restoring service after extended downtime. A manual authorized maintenance pass can call `app.interview_cleanup.cleanup()` in the API environment; it uses that environment's configured database and commits expiry deletion.

Monitor the generic `Interview expiry cleanup unavailable.` event, database capacity and API responsiveness. Diagnose SQL failures using controlled infrastructure tooling; the private interview HTTP boundary suppresses SQL exception details that could contain response/audio parameters. Do not enable SQL parameter/body logging or export transcripts, raw audio, keys or provider payloads into operational reports. There is no Admin read access to learner sessions. History/recording APIs remain owner-only regardless of Admin role.

## Key, request and processing policy

Learners save their own encrypted Gemini Developer API key through existing settings, then explicitly enable interview processing at `/settings/interviews`. Separate free-project/billing-disabled attestation and Google processing consent are required. A key alone does not prove Free Tier or disable billing. The app cannot provide a technical zero-billing guarantee; do not enable billing for this feature or describe 18 attempts as a guaranteed provider-free allowance.

The interview provider is a fixed Gemini Flash-Lite REST policy in `api/app/interview_provider.py`; it has no Admin/CLI/custom-endpoint/other-provider fallback. It sends one bounded request with no retries/redirects, a 40-second HTTP timeout and 1,200 output-token cap. Device speech handles audible prompts/feedback without Gemini speech generation. Actual free quota is project-specific and may be shared with other apps.

Each session reserves at most 18 attempts durably, counting errors, audio transcription and later manual feedback retries. Only one provider request per learner may run across all tabs/sessions. PostgreSQL advisory locks on a dedicated connection survive reservation commits and private session deletion, and release on connection/process termination. Abandoned attempts stay charged; a new manual ID is required. Replayed IDs do not resend. Do not add background quota retries, reset counters, swap keys behind the learner or infer a universal quota reset time.

Confirmed text is immutable and feedback retries reuse it without audio transcription. Prompt/rubric snapshots retain their original reviewed version. Content changes, lost studied-topic eligibility or Stack deactivation block new work and preserve private self-review/history. Withdrawing consent or removing/replacing a key stops new processing. A late response must pass ownership, lifetime, eligibility and current processing checks; it never recreates deleted history/audio.

## Disable and rollback

Whisper is already disabled without an environment override. Do not install/enable it until the [benchmark gate](mock-interview-whisper-gate.md) has actual permissioned corpus and host/app measurements. Its eventual one-worker bounded queue/resource limits and rollback requirements are specified there; today's release has no worker jobs, model downloads or hidden inference costs.

A learner can disable interview AI/withdraw consent while retaining private self-review, or delete their session/key. To suspend the entire feature during an incident, use the existing operator maintenance/route controls after authorization, stop provider admission and allow privacy cleanup to run. Do not automatically downgrade private-evidence migrations as an operational rollback. Restore the previous compatible application version while retaining the database additions/cleanup, or follow a reviewed backup/migration recovery plan; removing tables deletes private history.

## Separately authorized rollout checklist

- Review the full branch (including its content-health baseline), confirm all eight ticket pushes and prepare the normal PR/main release process.
- Confirm the intended database, backup retention and recoverability; apply migrations/import once and verify repeated import plus Admin coverage.
- Verify HTTPS, private API ingress, 5 MB transport, FFmpeg and the running cleanup task in staging.
- Smoke-test target physical Android/iOS/desktop browsers, keyboard and an installed screen reader; the saved Chromium mobile viewport report is not a physical-device or Safari test. Keep unsupported-browser typing/self-review available.
- Use permissioned English accent/technical-term recordings and explicitly consented own Free Tier credentials for any live quality evaluation. Until then, report transcription/semantic feedback quality as unmeasured.
- Check consent decline, quota exhaustion, a removed key, private history, audio expiry and owner deletion. Preserve current provider budget/ownership guards.
- Merge/deploy only under a separate user instruction. No such action was performed for these tickets.
