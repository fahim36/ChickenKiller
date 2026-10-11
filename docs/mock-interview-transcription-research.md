# Whisper transcription options for guided mock interviews

Primary sources fetched on 11 October 2026 (UTC). Research only; no runtime or deployment changes.

## Findings

| Option | Free-provider constraint | Operational fit |
| --- | --- | --- |
| Open-source Whisper | Code and weights have an MIT license; inference needs no Gemini/OpenAI API call. | Reference Python/PyTorch implementation requires FFmpeg. Useful baseline, less attractive than optimized runtimes for a small server. [Official repository](https://github.com/openai/whisper). |
| faster-whisper on CPU | No per-transcription provider charge; CPU, RAM, storage and hosting still cost resources. | Python integration; CPU INT8 support, bundled audio decoding, optional VAD. A candidate server worker, subject to an actual host benchmark. [Official repository](https://github.com/SYSTRAN/faster-whisper). |
| whisper.cpp on server | No per-transcription provider charge; same hosting caveat. | CPU-only inference and quantization supported. Documented approximate memory: tiny 273 MB, base 388 MB, small 852 MB. These are implementation figures, not total container budgets. [Official repository](https://github.com/ggml-org/whisper.cpp). |
| whisper.cpp browser WASM | No transcription API quota; computation happens on the learner's device. | Official example keeps audio local. Model download, browser support and device speed are material usability costs. Benchmark before choosing it as the default. [Official browser example](https://github.com/ggml-org/whisper.cpp/blob/master/examples/whisper.wasm/README.md). |
| Hosted OpenAI transcription | A separate provider and billed API; incompatible with Gemini-key-only/free-provider scope. | Do not configure a paid automatic fallback. Current official pricing lists paid transcription rates. [Pricing](https://developers.openai.com/api/docs/pricing). |

Whisper supports English-only and multilingual models; smaller English-only models can be appropriate for English-only practice. Accuracy varies by language and hardware-dependent speed figures are not deployment promises. [Whisper models](https://github.com/openai/whisper#available-models-and-languages).

The faster-whisper published CPU benchmark uses eight threads on an Intel i7-12700K: small INT8 transcribed 13 minutes in 1m42s with 1,477 MB RAM. This does **not** establish performance on a shared VPS, phones, or many concurrent sessions. The implementation is MIT licensed. [Benchmark and license](https://github.com/SYSTRAN/faster-whisper).

The browser example describes tiny/base taking roughly 20–30 seconds for 60 seconds of audio on a modern CPU/browser; it requires WASM SIMD and downloads a roughly 74 MB tiny model. Its 120-second recording limit and greedy decoding are example constraints, not universal Whisper limits. This is feasibility evidence, not a supported-device guarantee. [WASM example](https://github.com/ggml-org/whisper.cpp/blob/master/examples/whisper.wasm/README.md).

The model card warns about invented text, repetition and unequal accuracy across accents/languages, and recommends evaluation in the intended domain. Transcription therefore needs correction before technical feedback; silence must not become an assessed answer. [Official model card](https://github.com/openai/whisper/blob/main/model-card.md).

## Repository deployment evidence

`deploy/vps/docker-compose.yml` runs Postgres, API and Next.js on one VPS. It declares no GPU or dedicated transcription worker and no CPU/memory allocation for one. `deploy/vps/README.md` does not establish production CPU/RAM capacity. The older Render-oriented `docs/deploy.md` does not prove current host capacity. No production hardware inspection was performed.

## Recommendation for the design interview

Whisper is a credible way to separate speech recognition from Gemini feedback: record answer → transcribe → learner confirms/corrects transcript → one bounded Gemini text request. Transcription would remain usable when Gemini quota is exhausted; the reviewed rubric remains available. This architecture is a proposal, not an approved decision.

Prefer a short benchmark of **server faster-whisper CPU INT8** and **browser whisper.cpp tiny/base** before choosing the default. Server processing offers a more uniform device experience but needs spare host capacity and queue management. Browser processing avoids shared inference load and audio upload, but device wait time and large initial downloads can undermine a low-friction experience. Neither choice is genuinely resource-free. Gemini direct audio should be compared separately for quota consumption and maintenance effort.

Proposed benchmark: consented 30–90-second technical answers, representative Bangladeshi English accents and code terms across four Stacks; silence/noise, weak mobile devices and desktop browsers. Measure technical-term errors, meaning-changing omissions, learner corrections, median/p95 response time, initial download/cold-start time, peak RAM/CPU and concurrent queue pressure. Compare English-only versus multilingual models if Bangla-English mixing is in scope. Set acceptable thresholds with the product owner before selecting a runtime.

If server processing wins, keep it outside API request workers, bound duration/size/concurrency, and retain audio only according to the eventual retention decision. If browser processing wins, feature-detect support, cache the model deliberately, explain download/waiting, and preserve a manual transcript/self-review alternative. Do not silently upload audio to another provider or auto-grade uncertain transcripts.

Open decisions: English-only versus code switching; actual production spare RAM/CPU; acceptable transcription delay; mobile-browser support target; audio retention and transcript correction flow. No API free quota, server throughput or accent-specific accuracy is assumed.
