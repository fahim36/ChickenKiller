# Gemini evidence for free-quota mock interviews

Verified against official Google documentation on 11 October 2026. This records provider facts and implementation implications, not settled product decisions. No provider calls, credentials, paid requests or implementation changes were made during research.

## Capability and free availability

The pricing page's Standard Free Tier columns list input and output as free of charge for `gemini-3.1-flash-lite`, `gemini-3.1-flash-live-preview`, `gemini-2.5-flash-native-audio-preview-12-2025`, `gemini-3.1-flash-tts-preview`, and `gemini-2.5-flash-preview-tts`. This is model availability subject to quota, not an unlimited allowance or proof that any supplied key is free-tier. Free-tier entries indicate Google product-improvement data use. [Official pricing](https://ai.google.dev/gemini-api/docs/pricing).

`gemini-3.1-flash-lite` is a stable model supporting audio input, text output, transcription and structured outputs. It does not support audio generation or Live API. Therefore it can support recorded-answer transcription and a separate text evaluation call; speech output requires a different capability. [Model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite).

Recorded audio can be sent inline or through the Files API. Audio understanding documentation includes WebM, OGG and M4A support. [Audio documentation](https://ai.google.dev/gemini-api/docs/audio). Live API supports continuous voice interaction; direct browser connections should use ephemeral tokens instead of long-lived API keys. [Live overview](https://ai.google.dev/gemini-api/docs/live-api). TTS is a distinct speech-generation capability. [Speech-generation documentation](https://ai.google.dev/gemini-api/docs/speech-generation).

## Quota handling

Limits measure requests per minute, input tokens per minute and requests per day. They apply per project, not per API key; adding keys to the same project does not create independent quotas. Daily quotas reset at midnight Pacific time, which must not be confused with this app's UTC Day. Model and project tiers affect limits; actual active limits are displayed in Google AI Studio and capacity is not guaranteed. Do not bake an unverified universal RPM/RPD number into the product. [Rate-limit documentation](https://ai.google.dev/gemini-api/docs/rate-limits).

Google recommends bounded exponential backoff with jitter for transient errors such as `429 RESOURCE_EXHAUSTED` and `503 UNAVAILABLE`, and no retries for invalid/request/access errors. SDKs may retry automatically, so application budgets must account for SDK behavior. [Troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting).

Design implication: preserve a pending turn and offer retry later when quota is exhausted; never treat missing transcription or feedback as a poor answer. A bounded session reduces consumption but cannot guarantee sufficient quota shared with other applications. Do not automatically upgrade, change billing, or fall back to an Admin paid key or CLI.

## Free-tier enforcement and verification limits

Google documents project tier and billing-plan inspection in AI Studio. Linking billing upgrades access; disabling billing on a project returns it to Free Tier. Exhausted prepaid credit does not automatically downgrade a paid project. Thus a project explicitly kept without billing is the documented operational route for free-only use. [Billing documentation](https://ai.google.dev/gemini-api/docs/billing).

The reviewed Developer API request/reference and key documentation did **not establish** a request flag that refuses billed execution, or a reliable billing-tier lookup using only a supplied Gemini API key. This is a bounded research finding, not a claim that no Google Cloud administrative API can inspect billing with additional authorization. The documented response `serviceTier` distinguishes standard/flex/priority inference, not Free/Paid project billing tier. Selecting standard inference does not establish free billing. [Generate-content reference](https://ai.google.dev/api/generate-content), [API-key documentation](https://ai.google.dev/gemini-api/docs/api-key).

A successful inference, token counter or model allowlist alone cannot prove that the key's project has billing disabled. Learner confirmation that a key belongs to a Free Tier project is an attestation, not technical enforcement. If a hard machine-enforced zero-billing guarantee is required, launch must wait for a verified project/billing control mechanism; do not display such a guarantee based on attestation alone.

## Fit with the existing app

The app already stores Gemini Developer API keys encrypted with Fernet, but selects own key, Admin key and CLI fallbacks for legacy grading (`api/app/llm_keys.py`). Interviews need an explicit provider policy independent of those fallbacks. Existing settings promise grading-only use, so audio transcription and interview feedback require updated use disclosure. No Vertex credentials or additional provider subscription is necessary for the proposed Developer API route.

Recommended architecture to evaluate: short recorded turns through the server to the existing stable Flash-Lite model, transcript confirmation, then text feedback/follow-up; optional device speech playback avoids a second Gemini speech-model quota. This is an inference about simplicity and quota consumption, not a measured quality result. Validate technical-term transcription and feedback against representative samples before launch.
