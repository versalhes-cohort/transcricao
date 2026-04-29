# Transcrição Universal — Fullstack Architecture Document

> **Status:** Draft v1.0
> **Created by:** @architect (Aria)
> **Date:** 2026-04-29
> **Source:** `docs/prd.md` v1.0 (by @pm Morgan), `docs/brief.md` v1.0 (by @analyst Atlas)
> **Next agent:** @sm (River) — for Story 1.1 drafting via `*draft`

---

## Table of Contents

1. [Introduction & Architectural Stance](#1-introduction--architectural-stance)
2. [Deployment Topology](#2-deployment-topology)
3. [Request Flow](#3-request-flow)
4. [Module Structure](#4-module-structure)
5. [Audio Chunking Algorithm](#5-audio-chunking-algorithm)
6. [Error-Handling Architecture](#6-error-handling-architecture)
7. [Streamlit Session Model](#7-streamlit-session-model)
8. [Security Review](#8-security-review)
9. [Test Strategy](#9-test-strategy)
10. [Architectural Decision Records](#10-architectural-decision-records)
11. [Constitutional Compliance Trace](#11-constitutional-compliance-trace)
12. [Open Risks & Mitigations](#12-open-risks--mitigations)
13. [Change Log](#13-change-log)

---

## 1. Introduction & Architectural Stance

This document describes the technical architecture for **Transcrição Universal**, a single-user-class web application that converts arbitrary video URLs into clean PT-BR transcriptions. The architecture is intentionally **boring, monolithic, and synchronous** — every design choice is biased toward delivering the MVP within 2 weeks at <$10/month operating cost rather than toward scalability or extensibility.

### Architectural Principles (Project-Specific)

1. **Boring tech wins.** Streamlit + Python + Whisper + yt-dlp are mature, well-documented, and zero-novel-R&D. No exciting tech is required to ship this.
2. **Synchronous over async.** WebSocket session holds connection during processing. No job queues, no polling, no reconciliation. The 60-min input cap (FR4) is the load-bearing constraint that makes this safe.
3. **Stateless over persistent.** No database, no cache, no transcript storage (NFR10). Audio files are deleted immediately post-transcription (FR13).
4. **Fail loud at startup, fail soft at runtime.** Missing `OPENAI_API_KEY` crashes the app at boot (FR4 in Story 1.4 AC9). Runtime errors degrade gracefully with PT-BR messages (NFR11, FR12).
5. **Delegate cost control to OpenAI.** Application code does NOT track spending (PRD Technical Assumptions). The $20/month OpenAI account spending cap is the sole circuit breaker.

### What This Architecture Is NOT

- It is **not horizontally scalable.** A single concurrent transcription is the assumed mode (NFR15). Concurrent submissions may queue, fail, or degrade — accepted trade-off.
- It is **not multi-tenant.** No user accounts, no isolation, no quotas. The shared OpenAI cost cap protects the owner; trust is granted via URL sharing.
- It is **not internationalized.** All UI/error text is hardcoded PT-BR (NFR12). i18n is Phase 2.

### Out-of-Scope (Per PRD)

Authentication, transcript history, multilingual transcription, speaker diarization, timestamps, SRT/VTT export, streaming transcription, video preview, batch submission, webhooks, custom Whisper models, and analytics dashboards are all explicitly excluded.

---

## 2. Deployment Topology

### 2.1 Platform: Railway (single service)

A single Railway service runs the entire application as one Dockerized Python process. There is no separate backend, no CDN, no load balancer, no queue, no database. Railway provides HTTPS termination, public URL provisioning, environment-variable injection, and stdout log capture out of the box (NFR4, NFR5).

### 2.2 Container Strategy: Dockerfile (chosen over Nixpacks)

**Decision:** Use an explicit `Dockerfile` rather than Nixpacks auto-detection.

**Rationale:**
- `ffmpeg` is a mandatory system dependency (PRD Technical Assumptions, NFR4) and Dockerfile makes its installation deterministic and version-pinnable.
- Nixpacks can install `ffmpeg` via Nix providers, but the resulting image layering is opaque and harder to debug if a build breaks.
- Dockerfile cost: ~30 lines of code, one-time write. Worth the determinism.

### 2.3 Dockerfile Skeleton (reference)

```dockerfile
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Streamlit must bind to Railway's $PORT
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501
CMD streamlit run app/main.py --server.port=${PORT:-8501}
```

**Notes:**
- `python:3.11-slim` keeps image size minimal (~150 MB base + ~80 MB deps + ~60 MB ffmpeg ≈ 290 MB total).
- `STREAMLIT_SERVER_HEADLESS=true` disables Streamlit's "open browser" auto-launch (Railway runs headless).
- `${PORT:-8501}` defaults to 8501 locally and uses Railway's injected `$PORT` in production.

### 2.4 `requirements.txt` (pinned versions — Story 1.1 AC2)

Exact versions to be locked at first install; these are reference targets:

```
streamlit==1.40.0
yt-dlp==2025.1.15
openai==1.55.0
pydub==0.25.1
```

Pin policy: **exact versions** for all four direct dependencies. Transitive dependencies pinned via `pip-compile` (or accept Streamlit's default resolution at MVP). `yt-dlp` upgrades are documented in `RUNBOOK.md` (Story 1.7 AC9) and triggered by source-platform breakage rather than scheduled.

### 2.5 Environment Variables

| Variable | Required | Source | Purpose |
|---|---|---|---|
| `OPENAI_API_KEY` | YES | Railway dashboard | Whisper API authentication |
| `PORT` | YES (auto) | Railway-injected | HTTP port for Streamlit |
| `STREAMLIT_SERVER_*` | NO | Dockerfile ENV | Streamlit server config (set in image) |

`.env.example` (Story 1.1 AC4) lists `OPENAI_API_KEY=` (empty value). Real `.env` is gitignored. No other secrets exist at MVP.

### 2.6 Healthcheck

**Decision:** Use Streamlit's built-in `/_stcore/health` endpoint for Railway's healthcheck (returns HTTP 200 once the Streamlit server is ready). No custom `/health` route needed.

**Rationale:**
- FR14 requires a healthcheck-compatible endpoint; Streamlit provides this natively.
- Writing a custom Flask/FastAPI route alongside Streamlit doubles the process surface for zero benefit.
- `railway.toml` configures `healthcheckPath = "/_stcore/health"`.

**`railway.toml` skeleton:**

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/_stcore/health"
healthcheckTimeout = 60
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### 2.7 Cold Start Budget

NFR16 caps cold-start at 60 seconds. Realistic decomposition:
- Image pull + container start: ~10–15 s (Railway-side).
- Python interpreter + Streamlit boot: ~5–10 s.
- yt-dlp + openai SDK import: ~1–2 s.
- First WebSocket connection: ~1 s.

**Budget headroom:** ~30 s. If we trend toward the cap, the suspect will be Streamlit's WebSocket handshake on cold-cache CDN paths — NOT Python imports. Mitigation if it bites: keep the service warm via Railway's "always-on" tier (≈$0 incremental for hobby plans).

---

## 3. Request Flow

### 3.1 End-to-End Sequence (Happy Path)

```
USER                     STREAMLIT (Python process)              EXTERNAL
─────                    ─────────────────────────────            ────────
Paste URL
Click "Transcrever"
   │
   ▼
   ─────WebSocket frame────────▶
                            ┌─────────────────────────────────┐
                            │ 1. URL syntax validation        │
                            │    (errors.py: INVALID_URL)     │
                            └─────────────────────────────────┘
                            ┌─────────────────────────────────┐
                            │ 2. yt-dlp metadata fetch        │ ─────▶ Source platform
                            │    extract_info(download=False) │ ◀───── (returns metadata)
                            │    (errors.py: UNSUPPORTED_SOURCE)
                            └─────────────────────────────────┘
                            ┌─────────────────────────────────┐
                            │ 3. Duration cap check           │
                            │    duration > 3600s?            │
                            │    (errors.py: VIDEO_TOO_LONG)  │
                            └─────────────────────────────────┘
   ◀────st.status "Baixando áudio..."───
                            ┌─────────────────────────────────┐
                            │ 4. yt-dlp audio download        │ ─────▶ Source platform
                            │    → tempfile.mkdtemp()         │ ◀───── (returns audio bytes)
                            │    → audio.mp3 (≤64 kbps)       │
                            │    (errors.py: DOWNLOAD_FAILED) │
                            └─────────────────────────────────┘
   ◀────st.status "Transcrevendo..."───
                            ┌─────────────────────────────────┐
                            │ 5. File size inspection         │
                            │    if size ≤25 MB → single call │
                            │    if size >25 MB → chunk plan  │
                            └─────────────────────────────────┘
                            ┌─────────────────────────────────┐
                            │ 6. Whisper API call(s)          │ ─────▶ OpenAI Whisper
                            │    language="pt"                │ ◀───── (returns text)
                            │    response_format="text"       │
                            │    (errors.py: TRANSCRIPTION_FAILED)
                            └─────────────────────────────────┘
                            ┌─────────────────────────────────┐
                            │ 7. Stitch (if chunked)          │
                            │    + append "Duração total: MM:SS"
                            └─────────────────────────────────┘
                            ┌─────────────────────────────────┐
                            │ 8. Cleanup tempfile (FR13)      │
                            │    finally: shutil.rmtree(tmp)  │
                            └─────────────────────────────────┘
   ◀────st.status "Pronto!"────
   ◀────render text + Copiar btn───
```

### 3.2 Error Path Map

Every numbered stage above has exactly one error category it can emit (centralized in `errors.py`, see §6). The contract is: any exception raised inside a stage is caught at the stage boundary, mapped to its category, surfaced via `st.error()` in PT-BR, and the user is returned to a usable input state (FR12, AC6 in Story 1.6) — without page reload.

| Stage | Failure Cases | Error Category |
|---|---|---|
| 1. URL syntax | malformed scheme, empty, whitespace-only | `INVALID_URL` |
| 2. Metadata fetch | yt-dlp DownloadError, ExtractorError, network | `UNSUPPORTED_SOURCE` |
| 3. Duration cap | duration > 3600 s | `VIDEO_TOO_LONG` |
| 4. Audio download | yt-dlp post-fetch failure, disk full, geo-block | `DOWNLOAD_FAILED` |
| 5. File inspection | (no user-facing failures expected) | — |
| 6. Whisper API | auth, rate limit, 5xx after retries, malformed audio | `TRANSCRIPTION_FAILED` |
| 7. Stitching | (no user-facing failures expected) | — |
| 8. Cleanup | best-effort; failures logged but never surfaced | — (server log only) |
| Top-level | uncaught any-exception | `UNEXPECTED` |

### 3.3 Pipeline Timeout Budget (60-min input ceiling)

For the worst-case 60-minute video:

| Stage | Estimated Time | Notes |
|---|---|---|
| 1. URL validation | <10 ms | Regex + scheme check |
| 2. Metadata fetch | 2–10 s | yt-dlp HTTP roundtrip |
| 3. Duration cap | <1 ms | Numeric compare |
| 4. Audio download | 30–120 s | Network + post-process |
| 5. Inspection | <100 ms | `os.path.getsize` |
| 6. Whisper | 60–180 s | ~3 chunks × ~50 s each (parallel possible) |
| 7. Stitching | <100 ms | String concat |
| 8. Cleanup | <500 ms | `rmtree` |
| **Total** | **~95–315 s** | Well under NFR1's 5-min cap for typical inputs |

**Ceiling stress case:** A 60-min interview at high source bitrate could push Whisper time to ~240 s if processed serially. If we observe NFR1 violations on edge cases, **parallel chunk transcription** (concurrent.futures.ThreadPoolExecutor with max_workers=3) is a low-risk optimization within the same architecture — flagged for Phase 2 only if measured to be needed (no premature optimization).

---

## 4. Module Structure

### 4.1 Repository Layout (confirms PRD §Technical Assumptions, with refinements)

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                # Streamlit entry point — UI flow + orchestration
│   ├── extractor.py           # yt-dlp wrapper (metadata + audio download)
│   ├── transcriber.py         # Whisper client + chunking + stitching
│   ├── duration.py            # MM:SS formatter (pure function)
│   ├── chunking.py            # NEW — chunk-boundary math (pure, testable)
│   ├── errors.py              # PT-BR error catalog + exception hierarchy
│   └── logging_config.py      # NEW — log filter that strips URL/transcript content
├── tests/
│   ├── test_duration.py       # MM:SS edge cases (Story 1.5 AC8)
│   ├── test_chunking.py       # Chunk math (Story 1.4 AC8)
│   ├── test_url_validation.py # URL allowlist (Story 1.2 AC8)
│   └── test_errors.py         # Category mapping coverage
├── Dockerfile
├── requirements.txt
├── railway.toml
├── .env.example
├── .gitignore
├── README.md
├── RUNBOOK.md                 # Story 1.7 AC9
└── docs/
    ├── brief.md
    ├── prd.md
    ├── architecture.md        # this file
    ├── smoke-tests.md         # Story 1.7 AC3
    └── stories/               # SDC outputs
```

### 4.2 Refinements vs. PRD Proposed Structure

The PRD's proposed structure listed `extractor.py` / `transcriber.py` / `duration.py` / `errors.py`. This architecture **adds two modules**:

1. **`chunking.py`** — Splits chunk-boundary math out of `transcriber.py` so it can be unit-tested as a pure function (Story 1.4 AC8 explicitly mandates testable chunk math). Mixing pure boundary logic with side-effectful API calls in one module makes that test harder.
2. **`logging_config.py`** — Implements the NFR10 + Story 1.3 AC8 requirement that logs include event metadata but NEVER URLs or transcript content. A custom `logging.Filter` enforces this at the framework level, removing the per-call-site discipline burden.

Both additions trace directly to existing requirements (Article IV — No Invention compliant; see §11).

### 4.3 Module Responsibilities (Single-Purpose, Testable Boundaries)

#### `app/main.py` — Streamlit UI + Orchestration
- Renders single-page UI (FR1, Story 1.2 AC1).
- Invokes pipeline stages in order (§3).
- Wires `st.status` for progress messages (FR10, Stories 1.3 AC4, 1.4).
- Catches stage-boundary exceptions and routes to `errors.py`.
- Renders result + duration line + "Copiar" button (Story 1.5).
- Implements top-level `UNEXPECTED` catch-all (Story 1.6 AC5).
- Boot-time check for `OPENAI_API_KEY` (Story 1.4 AC9) — `RuntimeError` raised here BEFORE Streamlit starts serving requests.

#### `app/extractor.py` — `yt-dlp` Wrapper
- `fetch_metadata(url) -> VideoMetadata` — calls `YoutubeDL({'quiet': True}).extract_info(url, download=False)`. Returns dataclass with `duration_seconds`, `source_domain`. Maps `yt_dlp.utils.DownloadError` → `UnsupportedSourceError`.
- `download_audio(url, target_dir) -> Path` — calls `YoutubeDL` with `format='bestaudio/best'`, `postprocessors=[FFmpegExtractAudio(preferredcodec='mp3', preferredquality='64')]`, `outtmpl=target_dir/'audio.%(ext)s'`. Returns absolute path. Maps download errors → `DownloadError`.
- **Never invokes yt-dlp via subprocess shell** (NFR7).

#### `app/transcriber.py` — Whisper Orchestration
- `transcribe(audio_path, expected_duration_s) -> str` — top-level. Inspects file size, dispatches to single-call or chunked path.
- Single-call path: `client.audio.transcriptions.create(file=f, model='whisper-1', language='pt', response_format='text')`.
- Chunked path: delegates boundary math to `chunking.py`, splits via `pydub.AudioSegment`, transcribes each chunk, calls `chunking.stitch_transcripts(...)`.
- Retry logic: 2 retries on `openai.APIError` with exponential backoff (Story 1.4 AC6). Other exceptions propagate.
- Maps final failure → `TranscriptionError`.

#### `app/chunking.py` — Pure Boundary Math
- `plan_chunks(file_size_bytes, audio_duration_ms, max_chunk_bytes=24*1024*1024, overlap_ms=2000) -> list[ChunkSpec]` — pure function returning chunk specifications (start_ms, end_ms). Fully unit-testable with no audio I/O.
- `stitch_transcripts(chunks: list[str], overlap_ms: int) -> str` — concatenates chunk transcripts with naive de-duplication at boundaries (see §5.3).
- No `pydub`/`ffmpeg` imports here — boundary math only. Audio-segment I/O lives in `transcriber.py`.

#### `app/duration.py` — MM:SS Formatter
- `format_duration(seconds: int) -> str` — pure, returns `"MM:SS"` with zero-padding. Edge cases per Story 1.5 AC8 (0, 30, 60, 61, 599, 600, 3599, 3600).

#### `app/errors.py` — PT-BR Catalog + Exception Hierarchy
See §6.

#### `app/logging_config.py` — Safe Logging
See §6.4.

### 4.4 Module Dependency Graph

```
main.py
  ├──▶ extractor.py ──▶ yt_dlp (3rd party)
  ├──▶ transcriber.py ──▶ openai (3rd party)
  │      └──▶ chunking.py (pure)
  │      └──▶ pydub (3rd party)
  ├──▶ duration.py (pure)
  ├──▶ errors.py (pure)
  └──▶ logging_config.py
```

**Properties:**
- No circular dependencies.
- Pure modules (`chunking.py`, `duration.py`, `errors.py`) have zero 3rd-party imports → trivially testable.
- Side-effectful modules (`extractor.py`, `transcriber.py`) wrap exactly one 3rd-party SDK each → mockable boundaries.

---

## 5. Audio Chunking Algorithm

### 5.1 Library Choice: `pydub` (over `ffmpeg-python`)

**Decision:** `pydub` for in-process audio splitting.

**Comparison:**

| Criterion | `pydub` | `ffmpeg-python` |
|---|---|---|
| API ergonomics | Pythonic (`audio[start_ms:end_ms]`) | Builder-pattern around CLI flags |
| Performance | Loads file into memory | Streams via subprocess |
| Memory at 60 min, 64 kbps MP3 | ~28 MB raw + ~56 MB decoded ≈ 84 MB | ~5–10 MB streaming |
| ffmpeg dependency | Required (already in image) | Required (already in image) |
| Error surface | Pydantic exceptions | Subprocess return codes |

**Rationale for pydub:**
- Memory cost (~84 MB peak) sits well within NFR8's implicit ~500 MB process budget (brief §Performance Requirements). Not a constraint at this volume.
- `pydub`'s slicing API (`audio[start:end]`) makes the chunking math trivial to express and test — directly aligns with Story 1.4 AC8.
- `ffmpeg-python` would re-introduce subprocess invocation patterns that NFR7 already constrains for `yt-dlp`. Same skill not transferring.
- If memory becomes a concern (very unlikely at 60-min cap), swap to `ffmpeg-python` is mechanical — `chunking.py` boundary math is unchanged.

### 5.2 Chunk-Plan Algorithm

**Inputs:**
- `file_size_bytes` — actual bytes on disk after yt-dlp extraction.
- `audio_duration_ms` — total duration of audio (from yt-dlp metadata × 1000).
- `max_chunk_bytes = 24 * 1024 * 1024` — 24 MB target (1 MB safety margin under Whisper's 25 MB limit, per Story 1.4 AC3).
- `overlap_ms = 2000` — 2-second overlap (Story 1.4 AC3).

**Algorithm:**

```python
def plan_chunks(file_size_bytes, audio_duration_ms,
                max_chunk_bytes=24*1024*1024, overlap_ms=2000):
    # Approximate ms per byte (assumes uniform CBR — acceptable for 64 kbps MP3)
    ms_per_byte = audio_duration_ms / file_size_bytes

    # Target chunk duration in ms (rounded down to integer)
    chunk_duration_ms = int(max_chunk_bytes * ms_per_byte)

    # Effective stride accounts for overlap
    stride_ms = chunk_duration_ms - overlap_ms

    chunks = []
    cursor_ms = 0
    while cursor_ms < audio_duration_ms:
        end_ms = min(cursor_ms + chunk_duration_ms, audio_duration_ms)
        chunks.append(ChunkSpec(start_ms=cursor_ms, end_ms=end_ms))
        if end_ms >= audio_duration_ms:
            break
        cursor_ms += stride_ms
    return chunks
```

**Properties:**
- Correctly produces a single chunk if `file_size_bytes <= max_chunk_bytes` (caller bypasses chunking entirely; this function is only invoked when chunking is needed).
- Final chunk's `end_ms` is clamped to `audio_duration_ms` — never overruns.
- Adjacent chunks overlap by exactly `overlap_ms` (except possibly the final pair if clamping shortens the last chunk).
- Pure function — fully unit-testable per Story 1.4 AC8.

**Worked example (60-min video, 28 MB file):**
- `ms_per_byte` = 3,600,000 / (28 × 1024 × 1024) ≈ 0.1226 ms/byte
- `chunk_duration_ms` = 24 × 1024 × 1024 × 0.1226 ≈ 3,084,000 ms (~51.4 min)
- One chunk would actually fit, but file size > 25 MB triggered chunking → produces 2 chunks: [0–3,084,000] and [3,082,000–3,600,000].

**Worked example (long-form 90-min video, 42 MB file — even though PRD caps at 60 min, validates algorithm):**
- `ms_per_byte` ≈ 0.1226
- `chunk_duration_ms` ≈ 3,084,000 ms (~51.4 min)
- `stride_ms` ≈ 3,082,000 ms
- Chunks: [0–3,084,000], [3,082,000–5,400,000] → 2 chunks.

### 5.3 Stitching Algorithm

```python
def stitch_transcripts(chunks: list[str], overlap_ms: int) -> str:
    # MVP heuristic: simple concatenation with light boundary cleanup.
    # The 2-second overlap window produces ~5–15 duplicated words at most chunk seams.
    # We attempt sentence-boundary alignment; if no boundary found, accept the duplicate.
    if len(chunks) == 1:
        return chunks[0]

    result = chunks[0]
    for next_chunk in chunks[1:]:
        # Strategy: find longest matching trailing/leading n-gram (5–20 words) and elide.
        merged = _merge_at_boundary(result, next_chunk, max_overlap_words=25)
        result = merged
    return result
```

**`_merge_at_boundary` heuristic (MVP):**
1. Take last `N=25` words of `result` (`tail`).
2. Take first `N=25` words of `next_chunk` (`head`).
3. Find the longest suffix of `tail` that is a prefix of `head` (case-insensitive, normalized punctuation).
4. If overlap ≥ 3 words → elide the overlap (keep `result` unchanged, append `next_chunk` from after the overlap).
5. If overlap < 3 words → concatenate with a single space; minor duplication acceptable per Story 1.4 AC5.

**Why this is acceptable for MVP:** Per Story 1.4 AC5, *"minor duplication at chunk seams is acceptable for MVP if no clean boundary is found."* This heuristic is good enough for personal-utility use; perfect de-duplication is Phase 2.

### 5.4 Edge Cases

| Case | Handling |
|---|---|
| File ≤25 MB | Skip chunking entirely; single Whisper call. |
| File ≥25 MB but duration unknown (yt-dlp metadata missing duration) | Fail at metadata stage with `UNSUPPORTED_SOURCE` (already required by Stories 1.2 AC4 / FR4). |
| Single chunk produced but file is split-eligible | Acceptable; algorithm degenerates correctly. |
| Last chunk shorter than `overlap_ms` | Clamping handles it; no special case. |
| Whisper returns empty string for a chunk | Concatenated as empty contribution; no crash. Logged at DEBUG. |
| All chunks return empty (final transcript <10 chars) | Raise `TranscriptionError` → user sees PT-BR "Falha na transcrição..." instead of a blank result. Threshold of 10 characters chosen to tolerate trailing whitespace/punctuation while still rejecting silent-audio failures. (Decision locked 2026-04-29 — see §12 R8.) |

---

## 6. Error-Handling Architecture

### 6.1 Exception Hierarchy

```python
# app/errors.py

class TranscricaoError(Exception):
    """Base — never instantiated directly."""
    category: str  # set by subclass
    user_message_pt: str  # set by subclass

class InvalidURLError(TranscricaoError):
    category = "INVALID_URL"
    user_message_pt = "URL inválida. Cole um link começando com http:// ou https://."

class UnsupportedSourceError(TranscricaoError):
    category = "UNSUPPORTED_SOURCE"
    user_message_pt = "Não foi possível acessar este vídeo. Verifique o link ou tente outra fonte."

class VideoTooLongError(TranscricaoError):
    category = "VIDEO_TOO_LONG"
    user_message_pt = "Vídeo excede o limite de 60 minutos. Tente um vídeo mais curto."

class DownloadError(TranscricaoError):
    category = "DOWNLOAD_FAILED"
    user_message_pt = "Falha ao baixar o áudio. Tente novamente ou use outra fonte."

class TranscriptionError(TranscricaoError):
    category = "TRANSCRIPTION_FAILED"
    user_message_pt = "Falha na transcrição. Tente novamente em alguns minutos."

class UnexpectedError(TranscricaoError):
    category = "UNEXPECTED"
    user_message_pt = "Algo deu errado. Tente novamente em alguns minutos."
```

`TIMEOUT` is mentioned in Story 1.6 AC1. At MVP the synchronous flow has no explicit timeout layer (Streamlit holds the WebSocket; Whisper has its own SDK-level timeout). If a wall-clock cap is added in Phase 2, a `TimeoutError(TranscricaoError)` subclass will be added then. For now, timeouts surface as `TRANSCRIPTION_FAILED` or `DOWNLOAD_FAILED` depending on which stage stalls — covered.

### 6.2 Mapping Pattern (Stage Boundary)

```python
# Pattern used at every stage boundary in main.py
try:
    metadata = extractor.fetch_metadata(url)
except UnsupportedSourceError as e:
    log_event("metadata_failed", url_hash=hash_url(url), category=e.category)
    st.error(e.user_message_pt)
    return  # back to input state
```

**Mapping happens INSIDE each module** (`extractor.py` raises `UnsupportedSourceError`, never lets `yt_dlp.utils.DownloadError` leak). This keeps `main.py` purely orchestration; modules encapsulate their error vocabulary.

### 6.3 Top-Level Catch-All (Story 1.6 AC5)

```python
# main.py — outermost wrapper around the pipeline
try:
    run_pipeline(url)
except TranscricaoError as e:
    # All known categories — already user-friendly
    st.error(e.user_message_pt)
except Exception as e:
    # Genuinely unexpected — log full traceback server-side, show generic PT-BR
    logger.exception("Unexpected error in pipeline")
    st.error(UnexpectedError().user_message_pt)
```

**Note:** Streamlit's own error boundary will display tracebacks if we let exceptions escape. The wrapper above is mandatory to prevent that (Story 1.6 AC5).

### 6.4 Logging Strategy (NFR10 + Story 1.3 AC8)

**Principle:** Logs include event metadata; logs NEVER include URLs (full) or transcript content.

**Implementation — `app/logging_config.py`:**

```python
import hashlib, logging, re

URL_PATTERN = re.compile(r'https?://[^\s<>"]+')

class SafeLogFilter(logging.Filter):
    """Redact full URLs in log records to prevent leakage."""
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = URL_PATTERN.sub('[URL]', record.msg)
        if record.args:
            record.args = tuple(
                URL_PATTERN.sub('[URL]', str(a)) if isinstance(a, str) else a
                for a in record.args
            )
        return True

def hash_url(url: str) -> str:
    """8-char hash for cross-event correlation without exposing the URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:8]

def setup_logging():
    handler = logging.StreamHandler()  # stdout — Railway captures
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s | %(message)s'
    ))
    handler.addFilter(SafeLogFilter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])
```

**Log event vocabulary (single line per event):**

| Event | Fields (allowed) | Forbidden |
|---|---|---|
| `pipeline_start` | url_hash, source_domain, ts | full URL |
| `metadata_ok` | url_hash, duration_s, source_domain | URL, title |
| `download_ok` | url_hash, duration_s, file_size_bytes | URL, file path beyond temp dir name |
| `chunk_plan` | url_hash, n_chunks, total_size_bytes | per-chunk content |
| `transcription_ok` | url_hash, duration_s, n_chunks, latency_ms | transcript text |
| `error` | url_hash, category, exception_type | full traceback in user-facing log; full traceback OK in stderr |
| `pipeline_end` | url_hash, success, total_latency_ms | — |

**Caller-side discipline + `SafeLogFilter` defense in depth:** even if a developer accidentally logs a URL string, the filter substitutes `[URL]` before stdout flush. NFR10 compliance is structural, not procedural.

---

## 7. Streamlit Session Model

### 7.1 WebSocket Lifecycle

Streamlit maintains a WebSocket between the browser and the server for the entire user session. When the user clicks "Transcrever", the Python script re-runs from top to bottom in the **session's WebSocket-bound thread**. Any `st.status()`, `st.error()`, or render call pushes a frame to the browser over the same socket.

**Implication for our architecture:** the multi-minute pipeline runs *inside* a single Streamlit script execution. We do NOT need a job/polling pattern. NFR14 is structurally satisfied.

### 7.2 Reliability for ≤5-Minute Processing (NFR1)

Streamlit's WebSocket layer (Tornado-based) has the following timeout characteristics at v1.40:

- **No explicit script-execution timeout** by default.
- **WebSocket idle timeout:** 30 s of no data flow → close. We push `st.status` updates every stage (FR10), which keeps the socket non-idle.
- **Browser-side reconnect:** if the socket drops, Streamlit auto-reconnects within ~2 s. The script execution continues server-side, but the in-flight result may be lost from the user's view (the script does not restart).

**Failure modes to defend against:**

1. **User closes tab during processing** → Server keeps running until completion, then result is dropped. Audio cleanup (FR13) still happens because `try/finally` is set up. Wasted Whisper $ cost: ≤$0.20. Accepted.
2. **Network blip** → Browser reconnects, but in-progress execution is invisible. User likely retries, doubling cost on that input. Accepted at MVP volume.
3. **Server-side crash mid-pipeline** → Audio file may leak in `/tmp`. **Mitigation:** Container is ephemeral on Railway; `/tmp` is wiped on restart. So leakage is bounded to the current container lifetime. Acceptable.

### 7.3 Why a 60-Minute Input Cap Is Load-Bearing

The 60-min cap (FR4) is the architectural keystone that justifies the synchronous design:

- 60 min audio at 64 kbps → ~28 MB → 2 chunks → ~120 s total Whisper time.
- Plus ~60 s download + overhead → ~3-min wall-clock — well under the 5-min NFR1 budget.

If the cap were removed, even a 90-min video would push the pipeline past 5 min, breaking NFR1 and risking WebSocket reliability. **Removing or raising the 60-min cap requires re-architecting to async (Phase 2 work).**

### 7.4 Progress Updates Implementation

```python
# main.py — sketch
with st.status("Processando vídeo...", expanded=True) as status:
    status.update(label="Validando URL...")
    url_validation.validate(url)

    status.update(label="Buscando metadados...")
    metadata = extractor.fetch_metadata(url)

    status.update(label="Baixando áudio...")
    audio_path = extractor.download_audio(url, tmp_dir)

    status.update(label="Transcrevendo...")
    transcript = transcriber.transcribe(audio_path, metadata.duration_s)

    status.update(label="Pronto!", state="complete")
```

`st.status` blocks render messages in a collapsible expander. Each `update()` call pushes a frame over the WebSocket — keeping it warm. This satisfies FR10 and Story 1.3 AC4 / Story 1.4 status requirements.

### 7.5 Session State: Empty by Design

`st.session_state` is **not used** for transcript persistence. Each submission produces a transcript that is rendered directly and discarded on the next script rerun (NFR10). The "input field reset after success" behavior (Story 1.5 AC7) is achieved by setting a `st.session_state` key on success that is consumed by the input widget on next render — minimal use only.

---

## 8. Security Review

### 8.1 NFR Compliance Audit

| NFR | Requirement | Architecture Provision | Status |
|---|---|---|---|
| NFR3 | $20 OpenAI cap | Manual stakeholder action; documented in README + RUNBOOK; no app code | ✅ External control |
| NFR5 | HTTPS | Railway default ingress | ✅ Platform-provided |
| NFR6 | Secrets in env vars only | `OPENAI_API_KEY` only in Railway env; `.env.example` committed; `.env` gitignored | ✅ Documented |
| NFR7 | yt-dlp Python API + URL allowlist | `extractor.py` uses `yt_dlp.YoutubeDL`; `main.py` validates `http`/`https` schemes | ✅ Enforced |
| NFR10 | No transcript persistence | `tempfile` + `try/finally` cleanup; `SafeLogFilter` redacts URLs; no DB | ✅ Structural |

### 8.2 Threat Model (Personal-Utility Tier)

The threat model is intentionally lightweight given the deployment context (private URL shared with trusted circle, ~5 transcriptions/week).

**In-scope threats:**

1. **Command injection via URL** — Mitigated by NFR7: yt-dlp called via Python API, never via shell. No `subprocess.run(shell=True)` anywhere. URL never interpolated into a shell command.

2. **SSRF via crafted URL** — yt-dlp fetches arbitrary HTTP(S) URLs by design (it's the product feature). The risk is an attacker submitting `http://169.254.169.254/...` (cloud metadata) or `http://localhost:5432/...` (internal services). On Railway, internal metadata access is platform-mitigated (no IMDS by default), but the risk is real for self-hosting.

   **Mitigation at MVP:** Accepted residual risk. Railway's network isolation makes successful SSRF unlikely. Phase 2 enhancement: add a host-based denylist (RFC1918 private ranges, link-local, loopback) before passing URL to yt-dlp.

3. **Cost-DoS via long videos** — Mitigated by FR4 (60-min cap) + NFR3 ($20/month OpenAI cap). Worst-case cost ceiling = $20/month, hard.

4. **Cost-DoS via repeated requests** — At MVP, no rate limiting. NFR15 explicitly accepts that simultaneous requests may queue/fail. The OpenAI cap is the only protection. Accepted.

5. **PII exposure via transcripts** — NFR10: transcripts never persisted, never logged. If the user transcribes their own private content, the only place the text exists is on their own browser screen. OpenAI Whisper API does not retain content per their default API terms (data not used for training).

6. **Source-platform Terms-of-Service violations** — yt-dlp use to extract YouTube/Instagram audio is in a legal gray zone. This is the user's responsibility (the public URL is not auto-distributed; the owner shares it with their trusted circle). No architectural mitigation needed; documented in README disclaimer.

**Out-of-scope threats (deferred or accepted):**

- Sophisticated XSS via Streamlit-rendered transcript (Streamlit escapes by default; not a concern unless `unsafe_allow_html=True` is used — it must NOT be).
- CSRF (no auth, no state-changing endpoints).
- Account takeover (no accounts).
- Insider threat at OpenAI (accepted; standard for any AI-API-based product).

### 8.3 Secrets Handling Checklist

- [ ] `OPENAI_API_KEY` only ever read via `os.environ` — never hardcoded, never logged.
- [ ] `.env.example` documents the variable; real `.env` in `.gitignore`.
- [ ] Boot-time check raises `RuntimeError` on missing key (Story 1.4 AC9) — fail fast, fail visibly.
- [ ] Railway dashboard is the only place real values live (Story 1.7 AC2).
- [ ] Key rotation procedure documented in `RUNBOOK.md` (Story 1.7 AC9).

### 8.4 Dependency Pinning + Update Hygiene

- All four direct dependencies (`streamlit`, `yt-dlp`, `openai`, `pydub`) pinned to exact versions.
- `yt-dlp` is the most likely to need urgent updates (source platforms break it). RUNBOOK.md documents the upgrade flow: bump version in `requirements.txt`, push, Railway auto-redeploys.
- No automated dependency-update bot at MVP (Phase 2 if needed). Manual review preferred at this scale.

---

## 9. Test Strategy

### 9.1 Unit Test Surface (Required for MVP)

Per PRD Testing Requirements + per-story ACs:

| Module | Test File | Coverage Target | Source AC |
|---|---|---|---|
| `duration.py` | `tests/test_duration.py` | 100% — pure function with known edge cases | Story 1.5 AC8 |
| `chunking.py` | `tests/test_chunking.py` | 100% — pure function, all branches | Story 1.4 AC8 |
| URL validation (in `main.py` or extracted helper) | `tests/test_url_validation.py` | 100% — schema allowlist, malformed inputs | Story 1.2 AC8 |
| `errors.py` | `tests/test_errors.py` | All categories instantiable, all `user_message_pt` non-empty | Story 1.6 AC1 |

**Concrete test cases (non-exhaustive, illustrative):**

`test_duration.py`:
- `format_duration(0) == "00:00"`
- `format_duration(30) == "00:30"`
- `format_duration(60) == "01:00"`
- `format_duration(61) == "01:01"`
- `format_duration(599) == "09:59"`
- `format_duration(600) == "10:00"`
- `format_duration(3599) == "59:59"`
- `format_duration(3600) == "60:00"`

`test_chunking.py`:
- File ≤25 MB → caller bypasses; `plan_chunks` not invoked. Test boundary at 25 MB exactly.
- 28 MB / 60 min → 2 chunks with 2-s overlap; sum coverage = 100% of duration; final chunk clamped to total.
- Stitching: identical 25-word overlap → fully de-duplicated; no overlap → simple concat with single space; partial overlap < 3 words → concat (accept duplicate).

`test_url_validation.py`:
- `validate("https://youtube.com/watch?v=...")` → OK
- `validate("http://example.com")` → OK
- `validate("ftp://example.com")` → InvalidURLError
- `validate("")` → InvalidURLError
- `validate("   ")` → InvalidURLError (whitespace)
- `validate("javascript:alert(1)")` → InvalidURLError

### 9.2 What is NOT Unit-Tested (Deliberately)

- `extractor.py` — wraps `yt-dlp`; mocking yt-dlp would test the mock, not the system. Validated via manual smoke tests (§9.3).
- `transcriber.py` (Whisper API call path) — same reasoning. Real API exercised in smoke tests.
- `main.py` (Streamlit UI) — Streamlit's session model resists unit testing well; integration via manual smoke tests is the right tradeoff at MVP scale.

This is **explicitly aligned with PRD Testing Requirements:** *"Integration tests NOT required at MVP. The expensive components will be exercised via real manual testing of 5+ source types during deployment validation."*

### 9.3 Manual Smoke Test Suite (Story 1.7 AC3-4)

Documented in `docs/smoke-tests.md` (created during Story 1.7). Required cases:

| # | Source | Expected Outcome |
|---|---|---|
| 1 | YouTube long-form (10–30 min) | Full transcript + duration line in PT-BR |
| 2 | YouTube Shorts (<60s) | Full transcript + duration line |
| 3 | Instagram Reel | Full transcript + duration line |
| 4 | TikTok | Full transcript + duration line |
| 5 | Generic HTML page with embedded `<video>` | Full transcript + duration line |
| 6 | Video >60 min | PT-BR rejection: "Vídeo excede o limite de 60 minutos." |
| 7 | Malformed URL | PT-BR rejection: "URL inválida..." |
| 8 | Unreachable URL | PT-BR rejection: "Não foi possível acessar este vídeo..." |

Each pass is recorded with timestamp, source URL hash (not full URL — NFR10), and outcome. Story 1.7 AC4–5 require all 8 to pass before launch.

### 9.4 No CI Gate at MVP

Per PRD: tests run locally before deploy. CI pipeline is Phase 2. Acceptable at this scale.

---

## 10. Architectural Decision Records

Inline ADRs — captured here rather than separate files to keep the doc unified.

### ADR-001: Streamlit (over FastAPI + custom HTML)

**Context:** Brief left frontend choice as Open Question. PRD locked in Streamlit.

**Decision:** Streamlit.

**Consequences:**
- ✅ Single Python codebase, zero JS, faster build.
- ✅ Native progress UI via `st.status` — covers FR10 trivially.
- ✅ WebSocket session model holds during multi-minute processing (NFR14 satisfied structurally).
- ⚠️ UI customization is limited. Acceptable per "no branding at MVP".
- ⚠️ Streamlit's WebSocket reconnect on network blips can drop in-flight results. Accepted at MVP.
- ⚠️ Public URL exposes the Streamlit version banner; minor info disclosure. Accepted.

### ADR-002: Synchronous request flow (over async job + polling)

**Context:** Open Question in brief. PRD chose sync (NFR14).

**Decision:** Synchronous, single-process.

**Consequences:**
- ✅ Eliminates job storage, reconciliation, polling endpoints.
- ✅ Streamlit session naturally holds connection.
- ✅ ~5–10 person-days saved vs async refactor.
- ⚠️ Cap of 60 min input is load-bearing — removing it requires async. Documented in §7.3.
- ⚠️ Concurrent users degrade. Accepted per NFR15.

### ADR-003: pydub for chunking (over ffmpeg-python)

See §5.1 for full rationale.

### ADR-004: Dockerfile (over Nixpacks)

See §2.2 for full rationale.

### ADR-005: Streamlit's `/_stcore/health` for healthcheck (over custom endpoint)

See §2.6.

### ADR-006: Two new modules added to PRD's proposed structure

`chunking.py` and `logging_config.py` — see §4.2 for trace to existing requirements.

---

## 11. Constitutional Compliance Trace

Per Constitution Article IV (No Invention) and PRD Architect Prompt, every architectural decision must trace to a brief/PRD source. This section is the audit trail.

| Decision | Source |
|---|---|
| Single Railway service | PRD NFR4, brief §Hosting |
| Dockerfile + ffmpeg | PRD NFR4, brief §Architecture Considerations |
| `requirements.txt` pinning | PRD NFR13, Story 1.1 AC2 |
| Healthcheck = `/_stcore/health` | PRD FR14 (any healthcheck-compatible endpoint satisfies) |
| `OPENAI_API_KEY` env var | PRD NFR6, Story 1.4 AC9 |
| 60-min input cap | PRD FR4, brief Open Q resolved |
| URL allowlist (`http`/`https`) | PRD NFR7 |
| yt-dlp Python API only | PRD NFR7, Story 1.2 AC7 |
| Tempfile audio + cleanup | PRD FR13, Story 1.3 AC7 |
| Whisper `language="pt"` | PRD FR6, Story 1.4 AC2 |
| 24 MB chunk + 2-s overlap | Story 1.4 AC3 |
| MM:SS formatter | PRD FR9, Story 1.5 AC8 |
| Copy-to-clipboard button | PRD FR11, Story 1.5 AC5 |
| PT-BR error catalog | PRD FR12, Story 1.6 AC1 |
| Top-level catch-all | Story 1.6 AC5 |
| stdout logging, no transcripts | PRD NFR10, Story 1.3 AC8 |
| URL hash in logs | PRD NFR10 (forbids transcript content; URL hashing is a structural enforcement, not a feature) |
| `chunking.py` module split | Story 1.4 AC8 (testable boundary math) |
| `logging_config.py` module | PRD NFR10 + Story 1.3 AC8 (structural compliance) |
| pydub library | PRD §Technical Assumptions ("pydub recommended"); ADR-003 |
| 2 retries + exp backoff on Whisper | Story 1.4 AC6 |
| Streamlit session model | PRD NFR14 |
| HTTPS | PRD NFR5 |

**No architectural inventions.** Two new modules (`chunking.py`, `logging_config.py`) are structural decompositions of existing requirements, not new features. Flagged here for explicit user awareness.

---

## 12. Open Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Source-platform IP block (YouTube blocks Railway IP range) | Medium | High (sporadic failures) | Brief-documented; Phase 2 cookie-file support |
| R2 | yt-dlp upstream breakage | Medium | High (all transcriptions fail) | RUNBOOK upgrade procedure; pinned version |
| R3 | OpenAI Whisper outage | Low | Total outage during incident | Graceful PT-BR error; accepted |
| R4 | Streamlit WebSocket drop during long processing | Low | User loses in-flight result | st.status keeps socket warm; accepted |
| R5 | Audio file leak on container crash | Low | Bounded — container ephemeral | tempfile + try/finally; restart wipes `/tmp` |
| R6 | Chunk-stitching duplication artifacts | Medium | Cosmetic only | Heuristic dedup; "minor duplication acceptable" per Story 1.4 AC5 |
| R7 | Cold start exceeds 60 s | Low | First-request UX poor | Headroom budgeted in §2.7; warm-up via Railway always-on if needed |
| R8 | All chunks return empty transcript (silent failure) | Low | User sees blank result | **Resolved 2026-04-29:** raise `TranscriptionError` if final transcript length < 10 chars. To be implemented in Story 1.4. |
| R9 | SSRF via internal-network URL | Low | Information disclosure | Railway network isolation mitigates; Phase 2 host denylist |
| R10 | NFR1 (5-min) violated on edge-case 60-min videos | Low | UX failure | Parallel chunk transcription available as Phase 2 optimization within same architecture |

---

## 13. Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-04-29 | 1.0 | Initial fullstack architecture draft per PRD Architect Prompt (8 deliverables + ADRs + risks) | Aria |
| 2026-04-29 | 1.1 | Owner approved recommendations: `chunking.py` + `logging_config.py` modules confirmed; R8 resolved (raise `TranscriptionError` if transcript <10 chars) | Aria |

---

## Next Steps

### Handoff to @sm (River)

@sm — Architecture is complete. Story 1.1 (Project Foundation & Railway Deployment Canary) is ready for `*draft`. Use:

- `docs/prd.md` Story 1.1 ACs as the AC baseline.
- `docs/architecture.md` §2 (Deployment Topology) for technical specifics — Dockerfile skeleton, `requirements.txt` pin policy, `railway.toml` template, `.env.example` content, healthcheck path.
- `docs/architecture.md` §4.1 for the canonical repository layout (note: §4.2 adds `chunking.py` + `logging_config.py` beyond PRD's proposed structure — these are scoped into Stories 1.4 and 1.3 respectively, NOT Story 1.1).

### Confirmed Decisions (2026-04-29)

Owner (non-technical, deferring to architect recommendations) approved all pending items:

1. ✅ `chunking.py` — separate module for pure boundary math (Story 1.4 scope).
2. ✅ `logging_config.py` — structural NFR10 enforcement (Story 1.3 scope).
3. ✅ R8 — raise `TranscriptionError` if final transcript length <10 chars (Story 1.4 scope).

No further user confirmations required. Architecture is locked at v1.1; ready for story drafting.
