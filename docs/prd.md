# Transcrição Universal Product Requirements Document (PRD)

> **Status:** Draft v1.0
> **Created by:** @pm (Morgan)
> **Date:** 2026-04-29
> **Source:** `docs/brief.md` v1.0 (by @analyst Atlas)
> **Next agent:** @architect (Aria) — for technical architecture document

---

## Goals and Background Context

### Goals

- Enable any user with the public URL to transcribe a video from any major source (YouTube, Instagram, TikTok, embedded video pages, etc.) by pasting the URL into a single web form.
- Deliver clean, high-quality PT-BR transcriptions with no timestamps, speaker labels, or subtitle scaffolding — only the raw text plus total video duration in `MM:SS` format.
- Operate within a hard monthly cost ceiling of USD $20 (OpenAI spending cap) and a target operating cost of <$10/month at projected volume.
- Deploy a functional MVP on Railway within 2 weeks of approval, requiring zero technical knowledge from end users.
- Achieve ≥90% transcription success rate across the first 20 real-world submissions, validating universal source coverage.
- Keep architecture maximally simple: monolithic Streamlit app, synchronous request flow, no database, no authentication.

### Background Context

Today, transcribing online video content for personal use requires a brittle chain of manual steps (locate downloader, install tools, extract audio, upload to a transcription service) or paid SaaS subscriptions that are over-engineered for occasional use. Free web transcribers are unreliable on Instagram/embedded videos and produce poor PT-BR. Local tools demand technical comfort the target user does not have. **Transcrição Universal** addresses this gap with a single-purpose web app that combines `yt-dlp`'s 1000+-source extractor library with OpenAI's Whisper API to produce paste-ready Portuguese transcriptions — no install, no login, no subscription.

The economic foundation is straightforward: at the projected volume (~5 vídeos/week, mostly ≤30 min), Whisper API costs stay under $3/month, and Railway hosting adds ~$5/month. Cost ceiling is enforced via OpenAI's account-level spending cap rather than custom code, which is appropriate for a personal utility shared with a trusted circle. The MVP intentionally excludes authentication, history, multilingual support, and timestamps to compress scope and time-to-deploy.

### Change Log

| Date       | Version | Description                                            | Author |
|------------|---------|--------------------------------------------------------|--------|
| 2026-04-29 | 1.0     | Initial PRD draft from project brief, YOLO mode        | Morgan |

---

## Requirements

### Functional

- **FR1:** The system shall present a single-page web interface with one URL input field, one submit button, and one output area for the transcription result.
- **FR2:** The system shall accept any HTTP/HTTPS URL pointing to a source supported by `yt-dlp` (including but not limited to YouTube, Instagram, TikTok, Vimeo, Facebook, Twitter/X, and arbitrary HTML pages with embedded video).
- **FR3:** The system shall pre-validate the input URL for well-formed HTTP/HTTPS structure before initiating any backend processing, displaying an immediate user-facing error if validation fails.
- **FR4:** The system shall query the source for video metadata (duration in particular) **before** downloading the full audio, and shall reject any video whose duration exceeds **60 minutes** with a clear PT-BR error message ("Vídeo excede o limite de 60 minutos.").
- **FR5:** The system shall extract the audio-only stream of the source video via `yt-dlp`, downloaded to ephemeral storage in a compressed format (MP3 or M4A, ≤64 kbps preferred for size optimization).
- **FR6:** The system shall transcribe the extracted audio using OpenAI's Whisper API (`whisper-1` model) with the `language` parameter explicitly set to `"pt"`.
- **FR7:** When the extracted audio file exceeds the 25 MB Whisper API limit, the system shall automatically split the file into sequential chunks (with safe overlap to preserve sentence boundaries), transcribe each chunk independently, and concatenate the resulting transcripts in correct chronological order.
- **FR8:** The system shall render the full transcription as plain text in a scrollable output area, with no timestamps, no speaker labels, no formatting markers, and no segmentation breaks beyond natural paragraphing produced by Whisper.
- **FR9:** The system shall append `Duração total: MM:SS` as the final line of every successful transcription, where MM is total minutes and SS is the remaining seconds (zero-padded, e.g., `Duração total: 07:42`).
- **FR10:** The system shall display progress indicators with PT-BR status messages during processing (minimum: `"Baixando áudio..."`, `"Transcrevendo..."`), updating as the pipeline advances.
- **FR11:** The system shall provide a one-click "Copiar" button that copies the full transcription text (including the duration line) to the user's clipboard.
- **FR12:** The system shall display PT-BR user-friendly error messages — without raw stack traces or technical details — for at minimum: malformed URL, unsupported/unreachable source, video over 60 min, audio extraction failure, transcription API failure, and processing timeout.
- **FR13:** The system shall delete all downloaded audio files from ephemeral storage immediately after the transcription completes (success or failure), preserving no source media on the server.
- **FR14:** The system shall expose a simple unauthenticated `/health` endpoint (or equivalent Streamlit liveness behavior) returning HTTP 200 when the application is running, to support Railway healthchecks.

### Non Functional

- **NFR1:** Wall-clock processing time from URL submission to transcription display shall not exceed **5 minutes for videos ≤60 min** in duration under normal operating conditions (excludes API outages and source-platform blocking).
- **NFR2:** Monthly operating cost (Railway hosting + OpenAI API usage) shall remain below **USD $10** at projected volume of ~20 transcriptions/month.
- **NFR3:** OpenAI API spending shall be hard-capped at **USD $20/month** via the account-level spending limit configured directly on the OpenAI dashboard (manual stakeholder action, not application code).
- **NFR4:** The application shall be deployed as a **single Dockerized service on Railway**, with `ffmpeg` installed in the container image as a system dependency.
- **NFR5:** All HTTP traffic shall be served over HTTPS (provided by Railway's default ingress).
- **NFR6:** OpenAI API key and any other secrets shall be stored **exclusively** in Railway environment variables. No secret shall be committed to source control. The repository shall include a `.env.example` documenting required variables without values.
- **NFR7:** URL input shall be passed to `yt-dlp` via its Python API (`yt_dlp.YoutubeDL`) and never via shell-escaped string interpolation, eliminating command-injection risk. URLs shall additionally be validated against a schema-only allowlist (`http://`, `https://`).
- **NFR8:** The web interface shall be mobile-responsive, usable on screens ≥360 px wide without horizontal scroll on critical interactions (input + output + copy button).
- **NFR9:** The application shall support the latest 2 versions of Chrome, Firefox, Safari, and Edge on both desktop and mobile.
- **NFR10:** The system shall **not persist** transcribed content to any durable storage. No database, no log files containing transcript bodies, no caching beyond the active request lifecycle. Server logs may include event metadata (timestamp, URL hash, duration, success/failure) but never transcribed text.
- **NFR11:** The system shall fail gracefully when `yt-dlp` cannot access a source (IP block, DRM, geographic restriction). Failure shall produce a user-facing PT-BR error message; no crash, no 5xx response visible to the user.
- **NFR12:** All UI labels, status messages, error messages, and button text shall be in **PT-BR**.
- **NFR13:** The `yt-dlp` dependency shall be pinned to a specific version in `requirements.txt`, but the project shall include a documented procedure to upgrade `yt-dlp` (rebuild + redeploy) when upstream sources change format.
- **NFR14:** The architecture shall be **synchronous request-response** at MVP. The Streamlit WebSocket session shall hold the connection during processing, with progress updates pushed to the UI via `st.status` or equivalent.
- **NFR15:** A single concurrent transcription request shall be the assumed operating mode. The system is not required to handle parallel requests gracefully at MVP (simultaneous requests may queue, fail, or degrade — acceptable trade-off for personal-scale deployment).
- **NFR16:** Application startup time on Railway (cold start to ready-to-serve) shall not exceed 60 seconds.

---

## User Interface Design Goals

### Overall UX Vision

A radically minimal "single-purpose tool" interface — visually unmistakable about what it does and what step the user is at. The aesthetic should feel **utility-first and trustworthy**, not "AI flashy". Streamlit's default styling is acceptable; no custom theming required at MVP. The user opens the page, sees one input, pastes, clicks, waits with clear progress feedback, and copies the result. Everything else is noise.

### Key Interaction Paradigms

- **Single-input, single-action:** The page presents one prominent text input and one submit button. No menus, no tabs, no navigation, no settings panel.
- **Linear progress feedback:** During processing, status text updates in a fixed location ("Baixando áudio..." → "Transcrevendo..." → "Pronto!"), giving the user a clear mental model of pipeline progress.
- **Result-as-final-state:** Once transcription completes, the result occupies the dominant area of the page. The input remains visible above for resubmission, but the visual emphasis shifts to the output and the "Copiar" button.
- **Errors as inline status:** Errors appear in the same status area as progress messages — no modal dialogs, no red-banner alerts, no toast notifications. Just clear PT-BR text.

### Core Screens and Views

- **Main / Only Screen:** URL input field, submit button, status/progress area, transcription output area, copy-to-clipboard button. All on a single page with no routing.
- **Health endpoint:** `/health` — invisible to end users; returns HTTP 200 for Railway monitoring. (Streamlit may handle this implicitly via its default health behavior.)

### Accessibility: WCAG AA (best effort, not contractually mandated)

- Streamlit's default components meet most WCAG AA requirements out of the box (semantic HTML, keyboard navigation, contrast).
- No custom accessibility audits are required for MVP, but the team shall avoid intentionally breaking accessibility (e.g., no images-of-text for critical content, no color-only indicators).

### Branding

- **None at MVP.** Streamlit's default theme is acceptable.
- A simple page title ("Transcrição Universal" or owner-specified working name) and favicon may be set if effort is trivial (≤30 minutes), otherwise deferred.
- No custom fonts, no logos, no color palette required at MVP.

### Target Device and Platforms: Web Responsive

- Primary target: desktop browsers (Chrome, Firefox, Safari, Edge — latest 2 versions each).
- Secondary target: mobile browsers (same browsers on iOS Safari and Android Chrome). Layout shall reflow naturally; the single-input/single-output design has no fundamental mobile blockers.
- No native apps. No PWA installation features required.

---

## Technical Assumptions

### Repository Structure: Monorepo

A single repository contains the entire application, deployment configuration, and documentation. There is no need for separate frontend/backend repos given Streamlit unifies both layers in one Python codebase.

**Proposed structure (Architect to confirm):**
```
.
├── app/
│   ├── main.py            # Streamlit entry point
│   ├── extractor.py       # yt-dlp wrapper
│   ├── transcriber.py     # Whisper API client + chunking
│   ├── duration.py        # MM:SS formatter
│   └── errors.py          # PT-BR error message catalog
├── tests/
├── Dockerfile
├── requirements.txt
├── railway.toml           # or nixpacks.toml
├── .env.example
├── .gitignore
└── docs/                  # brief, prd, architecture, stories
```

### Service Architecture: Monolith

**CRITICAL DECISION:** The application is a **single-process synchronous monolith**. Streamlit serves both the UI and the request-handling logic in one Python process. There are no microservices, no message queues, no background workers, no separate API tier.

**Rationale:**
- Volume is ~5 transcriptions/week, single-user-at-a-time. Distributed architecture would be premature optimization.
- Streamlit's WebSocket session naturally holds the connection during multi-minute processing, sidestepping HTTP request-timeout concerns.
- Synchronous flow eliminates the complexity of job storage, polling, and reconciliation logic — keeps MVP scope tight.
- If Phase 2 introduces multi-user concurrent load, async architecture can be retrofitted; the cost of doing it now exceeds the cost of doing it later.

### Testing Requirements

**CRITICAL DECISION:** **Unit tests + manual smoke tests for MVP.**

- **Unit tests** required for: `duration.py` (MM:SS formatter logic), URL validation, audio chunking math (chunk boundaries, overlap, stitching).
- **Integration tests** NOT required at MVP. The expensive components (yt-dlp network calls, Whisper API calls) will be exercised via real manual testing of 5+ source types during deployment validation.
- **Manual smoke test checklist** required as part of the MVP-complete definition: at minimum, one successful transcription each from YouTube, Instagram (Reels), TikTok, a generic embed page, and one error case (e.g., 60-min cap rejection).
- **No CI test execution gate** at MVP. Tests can be run locally before deploy. CI pipeline is out of scope until Phase 2.

### Additional Technical Assumptions and Requests

- **Language/runtime:** Python 3.11+ (broad library compatibility; Streamlit, yt-dlp, openai SDK all well-supported).
- **Frontend framework:** **Streamlit** (latest stable). Rationale: zero-frontend-code path, native Python, fits Railway deployment model, 60-min hard cap keeps user wait time within Streamlit's WebSocket reliability window.
- **Audio extraction:** `yt-dlp` (latest stable, pinned in requirements.txt). Invoked via Python API (`yt_dlp.YoutubeDL`), never via subprocess shell call.
- **System dependency:** `ffmpeg` must be installed in the Docker image — required by both `yt-dlp` (for audio post-processing) and the chunking logic.
- **Audio chunking library:** `pydub` recommended for Python-native audio splitting; alternative is direct `ffmpeg` subprocess via `ffmpeg-python`.
- **Transcription:** OpenAI `whisper-1` API (no local Whisper, no Groq alternative at MVP). API key via Railway env var `OPENAI_API_KEY`.
- **Cost cap mechanism:** Manual stakeholder action — set $20/month spending limit on OpenAI account dashboard. Application code does NOT implement cost tracking at MVP.
- **Deployment:** Railway. Single service. Dockerfile-based or nixpacks-based deployment (Architect's choice). HTTPS by default.
- **Domain:** Railway-provided subdomain at MVP (e.g., `transcricao.up.railway.app`). Custom domain deferred to Phase 2.
- **Logging:** Application logs via stdout/stderr (Railway default capture). Log level INFO. **CRITICAL:** transcript bodies must NEVER be logged. Log only event metadata (timestamp, URL hash or first 50 chars, source detected, duration in seconds, success/failure, error category).
- **Cookies / authentication for sources:** Not implemented at MVP. If a video requires login (e.g., private IG reel), the system shall fail gracefully with a clear error. Cookie-file support is a Phase 2 enhancement.
- **Concurrency / rate limiting:** No application-level rate limiting at MVP. Sole protection is the OpenAI account spending cap.
- **Versioning:** Git tag releases (`v0.1.0` for MVP). No semantic versioning enforcement at this scale.
- **Constitutional Article IV (No Invention) compliance:** Every requirement above traces directly to a statement in `docs/brief.md` or an explicit user clarification during PRD elicitation. No invented features.

---

## Epic List

Given the small total scope, the MVP is delivered as a **single epic** with logically sequential, vertically-sliced stories. Each story produces deployable value; foundational concerns (Docker, Railway deploy, healthcheck) are handled in Story 1.1 to establish a deployable canary from day one.

- **Epic 1: Transcription MVP — End-to-End Universal Video Transcription on Railway**
  Deliver the complete MVP: a public Streamlit app on Railway that accepts a video URL, extracts audio, transcribes it via OpenAI Whisper in PT-BR, and returns plain text + total duration, with proper error handling and the 60-min hard cap.

> **Rationale for single-epic structure:** The brief specifies a tightly-scoped MVP (~6-8 stories of work) intended for a single deployable increment. Splitting into multiple epics would create artificial seams without delivering distinct value milestones. If during architecture review @architect identifies a meaningful split point (e.g., extraction pipeline as standalone milestone), the PRD can be amended. Cross-cutting concerns (logging, error handling, PT-BR text) are integrated into stories rather than deferred to a final cleanup epic.

---

## Epic 1: Transcription MVP — End-to-End Universal Video Transcription on Railway

**Epic Goal:** Deliver a complete, production-deployable, public web application on Railway that accepts any video URL from a `yt-dlp`-supported source, validates and length-caps the input, extracts the audio, transcribes it via OpenAI Whisper API in PT-BR, and renders the full transcription with total duration in `MM:SS` format — all with PT-BR UI/error messaging and zero authentication. The epic establishes the foundational deployment pipeline in Story 1.1 and incrementally builds the transcription pipeline through Story 1.7, with each story producing a deployable, testable increment.

### Story 1.1 Project Foundation & Railway Deployment Canary

As the project owner,
I want a minimal Streamlit application deployed and publicly accessible on Railway,
so that subsequent stories can incrementally add features against a working deployment baseline.

#### Acceptance Criteria

1: Repository initialized with `app/main.py` containing a minimal Streamlit page displaying "Transcrição Universal — pronto para uso" or equivalent placeholder text.
2: `requirements.txt` includes pinned versions of `streamlit`, `openai`, `yt-dlp`, `pydub` (or chosen chunking library), and any other direct dependencies.
3: `Dockerfile` (or `nixpacks.toml`) builds a Python 3.11+ container with `ffmpeg` installed as a system package and Streamlit configured to listen on Railway's expected port.
4: `.env.example` lists required environment variables (`OPENAI_API_KEY` minimum) without real values; actual `.env` is gitignored.
5: `railway.toml` (or Railway dashboard configuration) provisions a single service from the repository with HTTPS enabled.
6: The deployed URL renders the placeholder page over HTTPS within 60 seconds of cold start.
7: Railway healthcheck passes against the Streamlit process (HTTP 200 on the Streamlit endpoint).
8: A `README.md` documents local development (`streamlit run app/main.py`), deployment (Railway CLI or git-push), and required environment variables.
9: OpenAI account spending cap of USD $20/month is verified configured (manual stakeholder check; documented in README).

### Story 1.2 URL Input Form with Validation and Pre-Flight Length Cap

As an end user,
I want to paste a video URL and have its format and length pre-validated before any download begins,
so that I get fast feedback on bad inputs and never wait through a long download just to discover the video is too long.

#### Acceptance Criteria

1: The Streamlit page presents a single text input labeled "Cole aqui o link do vídeo" and a submit button labeled "Transcrever".
2: On submit, the URL is validated against an HTTP/HTTPS schema-only allowlist; malformed URLs trigger an immediate inline PT-BR error ("URL inválida. Cole um link começando com http:// ou https://.") without backend processing.
3: For valid URLs, the system invokes `yt-dlp` in metadata-only mode (`extract_info(download=False)`) to retrieve the video duration without downloading audio.
4: If `yt-dlp` cannot resolve the URL (unsupported source, unreachable, blocked), a PT-BR error is displayed: "Não foi possível acessar este vídeo. Verifique o link ou tente outra fonte."
5: If the resolved duration exceeds 60 minutes, the system displays "Vídeo excede o limite de 60 minutos. Tente um vídeo mais curto." and does not proceed.
6: If the resolved duration is ≤60 min, the UI transitions to a status state showing "Preparando download...", and Story 1.3's pipeline takes over.
7: All `yt-dlp` invocations use the Python API (`yt_dlp.YoutubeDL`); no subprocess shell calls.
8: Unit tests cover URL validation logic (valid/invalid schemas, empty input, whitespace).

### Story 1.3 Audio Extraction Pipeline with yt-dlp

As an end user,
I want the system to download just the audio track of my video efficiently,
so that the next pipeline step (transcription) has a minimal-size audio file ready.

#### Acceptance Criteria

1: After length validation passes (Story 1.2), the system invokes `yt-dlp` to download the audio-only stream of the source video.
2: Audio is downloaded in a Whisper-compatible format (MP3 or M4A) at a target bitrate of ≤64 kbps where the source allows, to minimize file size.
3: The downloaded file is written to an ephemeral location (Python `tempfile` directory or a known temp path inside the container).
4: While downloading, the UI status updates to "Baixando áudio..." (visible to the user via `st.status` or equivalent).
5: On `yt-dlp` failure (DRM, geo-block, source error), a PT-BR error is shown: "Falha ao baixar o áudio. Tente novamente ou use outra fonte." The downloaded partial file (if any) is cleaned up.
6: On success, the UI transitions to "Transcrevendo..." and the file path is passed to Story 1.4's transcription step.
7: The downloaded audio file is **deleted** from disk immediately after the transcription step completes (success or failure) — no source media persists on the server.
8: Logging: a single INFO log line records the source domain, audio duration in seconds, and downloaded file size in bytes — but NOT the URL itself or any media content.

### Story 1.4 Whisper Transcription with Automatic Chunking

As an end user,
I want the audio to be transcribed in PT-BR without me worrying about file size limits,
so that I get a complete transcription regardless of whether the video is 5 minutes or 60 minutes long.

#### Acceptance Criteria

1: The system reads the audio file produced by Story 1.3 and inspects its size in bytes.
2: If the file is ≤25 MB, it is sent to OpenAI's `whisper-1` API in a single request with `language="pt"` and `response_format="text"` (or equivalent plain-text response).
3: If the file is >25 MB, the system splits the audio into sequential chunks of ≤24 MB each (1 MB safety margin) using `pydub` or `ffmpeg`, with a 2-second overlap at chunk boundaries to prevent words being cut mid-utterance.
4: Each chunk is transcribed independently via the Whisper API with `language="pt"`. Chunk transcripts are then concatenated in chronological order to produce the final transcript.
5: When chunks overlap, the overlap region is de-duplicated using a simple sentence/word-boundary heuristic; minor duplication at chunk seams is acceptable for MVP if no clean boundary is found.
6: If the Whisper API returns an error (auth failure, rate limit, server error), the system retries up to 2 times with exponential backoff before surfacing a PT-BR error: "Falha na transcrição. Tente novamente em alguns minutos."
7: The final transcript text is held in memory only (no disk persistence) and passed to Story 1.5's rendering step.
8: Unit tests cover chunk-boundary math (correct chunk count for various file sizes, correct overlap, correct stitching of mock transcripts).
9: The OpenAI API key is read from `os.environ["OPENAI_API_KEY"]`; missing key raises a clear configuration error at app startup, not at first request.

### Story 1.5 Result Rendering, Duration Formatting, and Copy-to-Clipboard

As an end user,
I want to see the full transcription clearly on the page with the video's total duration at the end, and copy it with one click,
so that I can use the text immediately without manual reformatting or copy-tedium.

#### Acceptance Criteria

1: On successful transcription, the full transcript text is displayed in a scrollable, selectable text area (e.g., `st.text_area` with `height` sized to ~400px or `st.markdown` block — choice left to implementation).
2: The output contains NO timestamps, NO speaker labels, NO segment markers — only the raw transcript text as returned by Whisper, with natural paragraphing preserved.
3: Below the transcript text, a final line is rendered: `Duração total: MM:SS` where MM is total minutes (no leading zero suppression: 7 minutes → `07`) and SS is remaining seconds (zero-padded). Example: `Duração total: 23:08`.
4: The duration value comes from the `yt-dlp` metadata extracted in Story 1.2 — not recomputed from the audio file.
5: A "Copiar" button is rendered adjacent to the output. Clicking it copies the full text (transcript + duration line) to the user's clipboard via `st.clipboard` or a custom JS-injected approach if Streamlit lacks a native clipboard component at the time of implementation.
6: Successful copy displays a transient confirmation message ("Copiado!") that fades or persists for ~2 seconds.
7: After successful rendering, the input field is reset and ready to accept a new URL without page reload.
8: Unit tests cover the MM:SS formatter for: 0s, 30s, 60s, 61s, 599s, 600s (exact 10 min), 3599s (one second under 60 min), 3600s (60 min flat — edge of cap).

### Story 1.6 Comprehensive Error Handling and PT-BR Error Catalog

As an end user,
I want to receive clear, friendly PT-BR error messages whenever something goes wrong,
so that I understand what happened and what to try next, without seeing technical jargon or stack traces.

#### Acceptance Criteria

1: A centralized error-message catalog (`app/errors.py` or equivalent) is created mapping internal error categories to user-facing PT-BR messages. Categories at minimum: `INVALID_URL`, `UNSUPPORTED_SOURCE`, `VIDEO_TOO_LONG`, `DOWNLOAD_FAILED`, `TRANSCRIPTION_FAILED`, `TIMEOUT`, `UNEXPECTED`.
2: All exception-raising paths in the application catch their domain-specific exceptions and map them to one of the above categories before surfacing to the UI.
3: User-facing error messages contain NO Python stack trace, NO HTTP status codes, NO library names, NO file paths, NO API endpoint URLs.
4: Server-side logs (stdout) include the full technical detail (exception type, traceback, library context) for debugging — but NOT the source URL or any transcript content.
5: An `UNEXPECTED` catch-all wraps the top-level Streamlit handler so any uncaught exception produces a graceful PT-BR message ("Algo deu errado. Tente novamente em alguns minutos.") rather than a Streamlit error stack-trace dump.
6: After any error is displayed, the input field remains usable and the user can submit a new URL without page reload.
7: Manual test verification: submit a malformed URL, an unreachable URL, a video over 60 min, and (if possible) an invalid OpenAI API key configuration — all four cases produce friendly PT-BR errors with no technical leakage.

### Story 1.7 Production Deployment, Smoke Test Suite, and Launch

As the project owner,
I want the MVP fully deployed to Railway with documented smoke-test validation across diverse video sources,
so that I can confidently share the URL with my trusted circle knowing the most common source types are validated.

#### Acceptance Criteria

1: All previous stories (1.1–1.6) are complete and merged.
2: The application is deployed to Railway production with all environment variables (including `OPENAI_API_KEY`) configured via Railway dashboard.
3: A `docs/smoke-tests.md` file documents the manual smoke test suite: at minimum, one successful transcription from each of YouTube (long-form), YouTube Shorts, Instagram Reels, TikTok, and one generic HTML page with embedded video.
4: All five smoke-test cases pass with valid PT-BR transcriptions and correctly formatted duration lines.
5: One error case is also validated end-to-end on production: submitting a video >60 min produces the expected PT-BR rejection message.
6: OpenAI account spending cap of $20/month is verified active on the live API key being used in production (screenshot or dashboard confirmation in `docs/smoke-tests.md`).
7: The deployed URL is documented in `README.md` (or a deploy-info doc) along with rollback procedure (Railway dashboard rollback to previous build).
8: Cold-start time from Railway sleep to first responsive page is measured and recorded as a baseline; if it exceeds 60 seconds, an investigation note is added to known-issues.
9: A `RUNBOOK.md` (one page) lists: how to upgrade `yt-dlp`, how to rotate the OpenAI API key, how to inspect Railway logs, and how to roll back a bad deploy.

---

## Checklist Results Report

> _To be populated by `*execute-checklist pm-checklist` after PM and stakeholder review of this draft. Skipped during YOLO generation._

---

## Next Steps

### UX Expert Prompt

> **Skipping UX Expert handoff at MVP.** Streamlit auto-generates the UI from Python code. The minimal interaction (one input, one button, one output, one copy button) is fully specified in this PRD's "User Interface Design Goals" section and does not require dedicated design work. If Phase 2 introduces a custom HTML frontend or a brand identity, @ux-design-expert can be engaged at that time using this PRD plus a Phase 2 brief as input.

### Architect Prompt

@architect (Aria) — Please initiate **Architecture Mode** using `docs/prd.md` as primary input alongside `docs/brief.md` for context. Produce `docs/architecture.md` covering at minimum:

1. **Deployment topology** — Railway service definition, Dockerfile structure, environment variable map, healthcheck approach.
2. **Request flow diagram** — URL submission → metadata fetch → length validation → audio download → chunking decision → Whisper transcription → result render. Include error paths.
3. **Module structure** — Concrete file layout under `app/` with module responsibilities. Confirm or amend the proposed structure in "Technical Assumptions / Repository Structure".
4. **Audio chunking algorithm** — Detailed approach: chunk size selection, overlap strategy, transcript stitching logic. Choose between `pydub` and `ffmpeg-python`.
5. **Error-handling architecture** — Exception hierarchy, error category mapping, logging strategy that strictly excludes URL and transcript content.
6. **Streamlit session model** — Confirm WebSocket session lifecycle holds for ≤5-min processing; identify any timeout risks for the 60-min upper-bound case.
7. **Security review** — Validate NFR6 (secrets), NFR7 (URL sanitization, yt-dlp Python API usage), NFR10 (no transcript persistence). Flag any additional risks.
8. **Test strategy** — Confirm unit-test surface (FR4 chunking math, FR9 MM:SS formatter, URL validation, error mapping). Define minimal smoke-test scenarios for `docs/smoke-tests.md`.

Pay particular attention to:
- **NFR14 / sync request model viability** — confirm Streamlit's WebSocket holds reliably for 5-min processing; if not, recommend mitigations *before* implementation (not as Phase 2 rework).
- **Constitutional Article IV (No Invention)** — every architecture decision must trace to a PRD requirement. Flag any architectural addition not directly required by FR/NFR for explicit user buy-in.
- **Story 1.4 chunking math correctness** — get this right; bad chunking = bad transcripts.

After architecture is approved, hand off to **@sm (River)** for Story 1.1 drafting via `*draft`.
