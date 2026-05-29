# EVAL — Babel

> **Evaluation Date:** 2026-05-29  
> **Evaluator:** Automated Portfolio Review  
> **Maturity Level:** Production-Ready

---

## 1. Project Purpose & Problem Statement

Real-time multilingual speech transcription has traditionally required either expensive cloud APIs or sluggish local inference pipelines that make interactive use impossible. Babel solves this by delivering sub-second latency transcription and translation using a GPU-accelerated CTranslate2 backend (`faster-whisper large-v3-turbo`) with a custom streaming anti-flicker algorithm.

The use case extends beyond a simple demo: Babel is designed as a platform for spatial computing companions (Meta Ray-Ban glasses, Horizon OS overlays), where near-instantaneous audio-to-text translation in 99 languages has genuine utility. The project also documents an honest, warts-and-all attempt at LoRA fine-tuning for Hindi-specific accuracy improvements.

---

## 2. Technical Architecture

Babel follows a clean client-server WebSocket architecture:

**Frontend (`client/`):** React 19 + Vite with Zustand for state management and Framer Motion for animations. Captures microphone audio via the Web Audio API, encodes it as `int16` PCM at 16 kHz mono, and streams it over a WebSocket connection. Also supports system audio via WASAPI loopback and file upload through a standard REST endpoint.

**Backend (`server/`):** FastAPI with uvicorn handles both the WebSocket streaming endpoint (`/ws/stream`) and a REST file transcription endpoint (`/transcribe/file`). The core transcription engine is `faster-whisper large-v3-turbo` via the CTranslate2 backend, which provides 4–6× speedup over vanilla Whisper through int8 quantization.

**Streaming Algorithm — Local Agreement:** Instead of naively sending each partial transcription to the UI (which would cause visible flicker as the model changes its mind), Babel implements a Local Agreement algorithm: only transcript prefixes confirmed by *two consecutive overlapping windows* are committed to the display. This is a non-trivial engineering decision that directly addresses Whisper's well-known hallucination and flicker problem during streaming.

**VAD Integration:** Silero Voice Activity Detection acts as a gate, only passing audio segments with detected speech to the model and truncating inference when the speaker stops. This physically prevents the model from entering repetition loops on silence.

**Docker:** Multi-stage build using CUDA 12.8 runtime for the backend (GPU pass-through) and an Alpine Nginx serving stage for the frontend. Requires NVIDIA Container Toolkit.

---

## 3. Model & Algorithm Details

**Primary Model:** `faster-whisper large-v3-turbo` — a CTranslate2-compiled version of OpenAI's Whisper large-v3 with selective layer pruning. Runs with `task=translate` to produce direct English output from any source language.

**LoRA Fine-Tuning Attempt (Hindi):**
- Architecture: `openai/whisper-large-v3` base with PEFT LoRA (rank-32, 4-bit QLoRA)
- Dataset: Google FLEURS `hi_in` (~2 GB)
- Training: 3 epochs on RTX 5060 (8GB VRAM), learning rate `1e-4`
- Outcome: **WER degraded from 39.98% (baseline) to 74.91% (fine-tuned)**

The fine-tuning demonstrated catastrophic forgetting of the EOS token attention weights at the aggressive LR. The adapter learned Hindi phonetic patterns but corrupted sequence termination, causing infinite repetition loops (e.g., `"The molecules are moving fast. ???????..."`). The evaluation pipeline itself required debugging: Unicode NFC normalization mismatches and Whisper's native punctuation vs. FLEURS' clean text were inflating WER before being corrected.

**Production Decision:** The base `large-v3-turbo` model is used in production. The LoRA adapter is documented transparently as a learning artifact with an active improvement roadmap (lower LR, more data augmentation). This is honest engineering practice.

**Benchmark:**

| Model | WER (FLEURS hi_in, 100 samples) |
|---|---|
| `whisper-large-v3` baseline | 0.3998 |
| Babel LoRA fine-tuned | 0.7491 |

---

## 4. Strengths

- **Local Agreement streaming algorithm** is a sophisticated solution to a real Whisper deployment problem — not a toy demo.
- **VAD-gated chunking** prevents infinite repetition at the system engineering level, not by model post-processing.
- **Transparent LoRA failure reporting:** The benchmark results (including the degradation) are documented openly with root cause analysis. This is rare and valuable.
- **Docker GPU support** with CUDA 12.8 runtime is correctly implemented.
- **CI/CD** resolves real cross-platform issues: Windows-only `PyAudioWPatch` split into `requirements-windows.txt`, npm lockfile divergence resolved for Linux CI runners.
- **99-language auto-detection** with no user configuration needed.
- **Comprehensive API documentation** with WebSocket message format and Swagger UI.

---

## 5. Limitations & Known Gaps

- **LoRA adapter is not production-ready:** The fine-tuned model performs significantly worse than the baseline. The roadmap item to fix it (lower LR, data augmentation) is acknowledged but not yet implemented.
- **System audio capture requires manual Windows setup:** Enabling "Stereo Mix" via Windows Sound Settings is a manual, non-obvious step.
- **No speaker diarization:** Multiple speakers in a single stream are not distinguished.
- **No subtitle export (SRT/VTT):** Only live display; no persistent output format.
- **8GB VRAM ceiling:** `large-v3-turbo` requires GPU with sufficient VRAM; CPU fallback is documented but slower.
- **No authentication or rate limiting** on the FastAPI server — suitable for local use only.
- **Meta Ray-Ban companion mode** is listed as a roadmap item but not implemented.

---

## 6. Code Quality Assessment

The FastAPI backend is cleanly structured with a `pipeline/` directory separating system audio capture logic. The WebSocket handler correctly implements the ring buffer and Local Agreement algorithm. The React client uses Zustand idiomatically for streaming state.

**Documentation:** Excellent — architecture diagram, API reference with WebSocket message format, fine-tuning reproduction instructions, and honest benchmark results.

**Test coverage:** Not explicitly visible; no `tests/` directory in `server/`. The fine-tuning pipeline has `benchmark.py` and `eval_checkpoint.json` with detailed eval data.

**Docker:** Properly multi-stage with GPU support. Platform-specific dependency separation is a sign of mature cross-platform thinking.

**CI/CD:** GitHub Actions pipeline resolves non-trivial Windows/Linux divergences correctly.

---

## 7. Maturity Breakdown

| Dimension | Score | Notes |
|-----------|-------|-------|
| Functionality | 9/10 | Core streaming transcription is production-grade with real anti-flicker engineering |
| Code Quality | 7/10 | Clean architecture; limited test coverage visible |
| Documentation | 9/10 | Honest benchmark reporting and clear architecture diagrams |
| Scalability | 6/10 | Single-user local deployment; no auth, no multi-client management |
| Security | 5/10 | No auth on FastAPI server; local-only use assumed |
| **Overall** | **7.2/10** | **Impressive real-time ML engineering; LoRA work is a valuable honest artifact** |

---

## 8. Suggested Next Steps

1. **Retry LoRA fine-tuning with corrected hyperparameters** — reduce LR to `1e-5` or `5e-6`, add data augmentation (noise, speed perturbation), and evaluate with an LLM-as-Judge rather than strict WER to catch semantic correctness.
2. **Add SRT/VTT export and speaker diarization** using `pyannote.audio` to make Babel viable as a subtitle generation tool.
3. **Add FastAPI authentication (API key or token)** and a rate limiter for any deployment beyond localhost.

---

## 9. Verdict

Babel is one of the technically deepest projects in this portfolio. The Local Agreement streaming algorithm and VAD-gated chunking demonstrate real understanding of Whisper's failure modes rather than naively wrapping the API. The LoRA fine-tuning work, while ultimately producing a degraded model, is documented with rigorous honesty — including root cause analysis and a clear improvement roadmap — which is more valuable as a portfolio artifact than a quietly omitted failure would be. The project is production-ready for local deployment; its main gaps are authentication hardening and the unresolved Hindi adapter.
