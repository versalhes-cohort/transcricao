# Project Brief: Transcrição Universal (working name)

> **Status:** Draft v1.0
> **Created by:** @analyst (Atlas)
> **Date:** 2026-04-29
> **Next agent:** @pm (Morgan) — for PRD generation

---

## Executive Summary

A simple public web application that accepts any video URL (YouTube, Instagram, embedded video pages, etc.), automatically extracts the audio track, and returns a clean Portuguese (PT-BR) transcription of the full content along with the video's total duration. The product solves the friction of manually downloading, converting, and transcribing video content for personal/professional use, eliminating the need for installed software, technical knowledge, or fragmented tooling.

The MVP targets a single-user owner sharing the URL with a small trusted circle, prioritizing simplicity, low cost, and broad compatibility over scale or polish.

---

## Problem Statement

**Current state and pain points:**
- Transcribing online videos today requires a chain of manual steps: locate a downloader, choose a format, install tools (yt-dlp, ffmpeg), extract audio, upload to a transcription service, and copy the result.
- Existing free web transcribers (e.g., random "video to text" sites) are unreliable, ad-heavy, often fail on Instagram or embedded videos, and have inconsistent PT-BR quality.
- Paid tools (Otter, Descript, Riverside) require accounts, subscriptions, and are over-engineered for occasional personal use.
- Browser-based downloaders frequently break when platforms (YouTube, Instagram) change DRM or bot-detection.

**Impact of the problem:**
- 10–30 minutes of manual workflow per video for someone non-technical.
- Quality loss on PT-BR when generic tools default to English models.
- Total blocker when the source has access barriers (private embeds, anti-scrape protections, paywalls visible only via browser play).

**Why existing solutions fall short:**
- Web tools fail on edge cases (IG reels, embeds, age-gated content).
- Local tools require installation + technical comfort.
- SaaS transcribers are subscription-locked and overkill.

**Why now:**
- OpenAI Whisper API delivers state-of-the-art PT-BR transcription at ~$0.006/min — making personal-scale tooling economically trivial.
- `yt-dlp` covers 1000+ video sources with active maintenance, including most "barrier" cases.
- Cloud hosting (Railway) makes a private personal web app deployable and runnable for ~$5/month.

---

## Proposed Solution

**Core concept:**
A single-page web app: paste a URL → click "Transcribe" → receive the full PT-BR transcription + total duration in MM:SS format.

**High-level flow:**
1. User submits a URL via a single input field.
2. Backend invokes `yt-dlp` to extract the audio track (best available quality, MP3/M4A).
3. Audio is sent to OpenAI Whisper API with `language="pt"` for transcription.
4. Result is rendered as plain text, with `Duração total: MM:SS` appended at the bottom.
5. (Optional) Copy-to-clipboard button.

**Key differentiators:**
- **Universal source coverage** — leverages `yt-dlp`'s extractor library to handle YouTube, Instagram, TikTok, Vimeo, podcast players, and arbitrary HTML pages with embedded video.
- **Zero-friction UX** — no login, no settings, no format choices. One field, one button.
- **PT-BR-first** — language explicitly forced to Portuguese, avoiding the typical English-default fallback.
- **Clean output format** — no timestamps, no speaker labels, no SRT scaffolding. Just the text + final duration.

**Why this will succeed:**
- Solves a narrow, well-defined personal need with mature, battle-tested components (no novel R&D required).
- Owner controls cost ceiling via OpenAI spending cap — no risk of runaway expense.
- Volume is so low (~5 vídeos/week) that even worst-case API costs stay under $5/month.

**High-level vision:**
A "private utility" web app — a small but reliable tool the owner and their inner circle can rely on for fast, high-quality PT-BR transcription of any video on the internet.

---

## Target Users

### Primary User Segment: The Owner (and Trusted Circle)

**Profile:**
- Single primary user (the project owner) plus a small circle (estimated <10 people) given access via shared URL.
- Non-technical or moderately technical users — comfortable with web forms, not with CLI or installations.
- Brazilian Portuguese speakers consuming Portuguese-language content.

**Current behaviors and workflows:**
- Watches video content (YouTube, Instagram reels, embedded interviews, lectures) and frequently wants the textual content for note-taking, quoting, summarizing, or accessibility.
- Currently improvises with browser extensions, manual downloads, or copy-pasting auto-captions (which are often poor PT-BR).

**Specific needs and pain points:**
- Reliable transcription regardless of platform or embedding method.
- High-quality PT-BR output (correct accents, punctuation, proper nouns).
- No setup overhead — must work from a browser on any device.

**Goals they're trying to achieve:**
- Convert spoken video content into text for reference, study, or repurposing.
- Avoid the "tool hunt" cycle when a video can't be transcribed by their usual method.
- Get clean, paste-ready text output with minimal post-editing.

---

## Goals & Success Metrics

### Business Objectives

- **Deploy a functional MVP on Railway within 2 weeks** of brief approval.
- **Keep monthly operating cost under $10** (Railway hosting + OpenAI Whisper usage at projected volume).
- **Validate universal source coverage** — successfully transcribe at least one video from each of: YouTube, Instagram, TikTok, and a generic HTML page with embedded `<video>` during MVP testing.

### User Success Metrics

- User submits a URL and receives a complete transcription within **5 minutes for videos ≤60 min** in length.
- Transcription quality (subjective) rated as "usable without significant editing" for ≥90% of PT-BR submissions.
- **Zero technical knowledge required** — a non-technical user can complete a transcription on their first attempt without instructions.

### Key Performance Indicators (KPIs)

- **Success rate:** ≥90% of submitted URLs return a valid transcription (measured over first 20 real-world submissions).
- **Average time-to-transcription:** <2× video duration (e.g., 30-min video transcribed in <60 min wall-clock, including audio download).
- **Cost per transcription:** ≤$0.20 average (target ~$0.10 for typical 15-min video).
- **OpenAI cost ceiling:** Hard cap at $20/month enforced via OpenAI account spending limit.

---

## MVP Scope

### Core Features (Must Have)

- **URL input form:** Single text field accepting any URL, with submit button. Clear validation feedback if the URL is malformed.
- **Audio extraction via yt-dlp:** Backend downloads audio-only stream from the source URL. Handles YouTube, Instagram, TikTok, Vimeo, generic embeds, and any other source covered by `yt-dlp`'s extractors.
- **Whisper API transcription:** Submits extracted audio to OpenAI's `whisper-1` endpoint with `language="pt"` parameter. Handles audio chunking automatically for files exceeding the 25MB API limit.
- **Plain text output:** Displays full transcription as plain text in a scrollable text area or content block. No timestamps, no speaker labels, no formatting markers.
- **Duration display:** Appends `Duração total: MM:SS` at the bottom of the transcription.
- **Loading state:** Shows clear progress feedback ("Baixando áudio...", "Transcrevendo...") during processing.
- **Error handling:** User-friendly error messages for: unsupported URL, unreachable video, transcription failure, timeouts. No raw stack traces.
- **Copy-to-clipboard button:** One-click copy of the transcription text.

### Out of Scope for MVP

- User accounts, login, or authentication.
- Transcription history / saved transcriptions database.
- Multiple language support (English, Spanish, etc.) — PT-BR only at MVP.
- Speaker diarization (multi-speaker labeling).
- Timestamps or SRT/VTT subtitle export.
- Real-time / streaming transcription.
- Video preview or playback.
- Editing, summarization, or AI post-processing of the transcription.
- Mobile-native apps (web app must be mobile-friendly, but no iOS/Android binaries).
- Custom Whisper models, fine-tuning, or vocabulary injection.
- Translation features.
- Bulk URL submission or batch processing.
- Webhooks or API for programmatic access.
- Analytics dashboards.
- Theming, dark mode, or extensive UI customization.

### MVP Success Criteria

The MVP is successful when:
1. The owner can paste a URL from YouTube, Instagram, or a generic embed page and receive a complete, readable PT-BR transcription within 5 minutes for typical short videos (≤60 min).
2. The system handles at least 5 different source types correctly during real-world testing.
3. Monthly operating cost stays under $10 at the projected volume of ~20 videos/month.
4. A non-technical user can use the tool successfully on first attempt without any documentation.


---

## Technical Considerations

### Platform Requirements

- **Target Platforms:** Web app, accessible via any modern browser (desktop + mobile).
- **Browser/OS Support:** Latest 2 versions of Chrome, Firefox, Safari, Edge. Mobile responsive.
- **Performance Requirements:**
  - Transcription wall-clock time: <2× video duration for videos ≤60 min.
  - UI must remain responsive during backend processing (async job + polling, or streaming progress).
  - Memory footprint per transcription: <500MB peak (audio chunking for long files).

### Technology Preferences

- **Frontend:** Streamlit or Gradio (preferred for simplicity — auto-generated UI, single Python codebase). Alternative: minimal HTML+vanilla JS served by FastAPI if more UI control is desired.
- **Backend:** Python 3.11+ with `yt-dlp` (latest), `openai` SDK, `ffmpeg-python` for audio handling.
- **Database:** None at MVP. (Phase 2 may introduce SQLite for history.)
- **Hosting/Infrastructure:** Railway (confirmed by stakeholder). Single service, Dockerized Python app. Persistent volume not required at MVP.

### Architecture Considerations

- **Repository Structure:** Single-repo monolith. Top-level structure: `app/` (Python source), `requirements.txt`, `Dockerfile`, `railway.toml` (or `nixpacks.toml`).
- **Service Architecture:** Monolithic single-process app. No microservices, no message queue, no background workers (synchronous request → response is acceptable at this volume).
- **Integration Requirements:**
  - OpenAI API (Whisper endpoint) — requires API key in env var.
  - `yt-dlp` invoked as subprocess or via Python bindings.
  - `ffmpeg` binary required in container for audio chunking — must be installed in the Docker image.
- **Security/Compliance:**
  - OpenAI API key stored as Railway environment variable (never committed).
  - No PII storage at MVP (no user accounts, no logs of transcribed content beyond ephemeral request lifecycle).
  - Input validation on URL field to prevent SSRF and command injection in `yt-dlp` invocation (use `yt-dlp` Python API rather than shell-escaped string).
  - HTTPS enforced (Railway provides this by default).
  - **Cost protection:** Hard spending cap on the OpenAI account ($20/month) as primary control.

---

## Constraints & Assumptions

### Constraints

- **Budget:** Total operating cost should stay under $20/month. Whisper API cost capped via OpenAI account spending limit.
- **Timeline:** MVP target deployment within 2 weeks of brief approval.
- **Resources:** Solo developer (with AI agent assistance via AIOX). No designer, no QA team, no DevOps engineer.
- **Technical:**
  - OpenAI Whisper API has a 25MB file size limit per request → audio chunking required for long videos.
  - Railway free tier may sleep instances on inactivity → first request after idle may have a cold start.
  - YouTube and Instagram occasionally block cloud-provider IP ranges from `yt-dlp` requests (probabilistic, not guaranteed).

### Key Assumptions

- The owner and trusted circle will not generate enough volume to trigger Whisper rate limits.
- Most videos transcribed will be ≤60 min in duration (per stakeholder confirmation).
- Source platforms (YouTube, Instagram) will continue to be supported by `yt-dlp` upstream.
- Railway will remain a viable, low-cost hosting option for the project lifetime.
- PT-BR will be the dominant language; multilingual content (e.g., bilingual interviews) is acceptable as a "best effort" output.
- Users will tolerate up to 2× video duration as wall-clock processing time.
- A simple synchronous request-response model is acceptable; no need for async job queues at MVP.

---

## Risks & Open Questions

### Key Risks

- **Source-platform IP blocking:** Cloud IPs (Railway's range) may be rate-limited or blocked by YouTube/Instagram. *Impact:* sporadic transcription failures. *Mitigation:* support for cookie file via env var, document the workaround; consider residential proxy as Phase 2 fallback.
- **OpenAI cost overrun:** A bad actor with the URL could submit very long videos repeatedly. *Impact:* unexpected bill. *Mitigation:* OpenAI account spending cap (primary control); Phase 2 password gate or rate limit.
- **`yt-dlp` upstream breakage:** YouTube/Instagram silent format changes can break audio extraction. *Impact:* sudden tool failure. *Mitigation:* pin `yt-dlp` to a recent stable but auto-update on container rebuild; document the upgrade procedure.
- **Whisper API outage:** OpenAI service downtime blocks all transcriptions. *Impact:* total feature outage. *Mitigation:* graceful error message, accept as low-probability risk at MVP.
- **Long-video timeout:** Railway request timeout (typically 5 min) may be exceeded for full transcription pipelines on long videos. *Impact:* failures on edge-case content. *Mitigation:* either restrict input to ≤60 min OR implement async job pattern (background task + polling endpoint).
- **PT-BR transcription quality on noisy/low-quality audio:** Heavy accents, background noise, or low-bitrate sources may produce poor output. *Impact:* user dissatisfaction. *Mitigation:* document realistic expectations; consider Whisper `prompt` parameter to bias toward PT-BR vocabulary in Phase 2.

### Open Questions

- Should the MVP include a hard length cap (reject videos >60 min) or attempt them with risk of timeout? = Reject (validated by user)
- Sync vs. async architecture — is acceptable wait time enough to justify keeping it synchronous, or should a job/polling pattern be designed up front to avoid Phase 2 rework?
- What's the minimum acceptable UX for "loading" feedback? Spinner only, or progressive status messages ("Downloading audio... Transcribing...")?
- Should there be any per-IP rate limiting at MVP, or rely solely on the OpenAI cost cap?
- Frontend choice: Streamlit (faster build, less polish) or Gradio (similar) or a custom HTML/FastAPI UI (more polish, more work)?

### Areas Needing Further Research

- Comparing `yt-dlp` reliability with `yt-dlp-nightly` for Instagram and TikTok specifically.
- Best-practice patterns for audio chunking and re-stitching transcripts when crossing the 25MB Whisper API limit (overlap windows, sentence-boundary splits).
- Railway-specific deployment patterns for Python apps with `ffmpeg` system dependency.
- Cookie-based authentication patterns for `yt-dlp` to bypass IP-based blocking.
- Comparison of Whisper API PT-BR quality vs. Groq's Whisper API (cheaper, faster) and `faster-whisper` self-hosted.

---

## Appendices

### A. Research Summary

**Cost analysis (MVP volume):**
- 5 vídeos/week × ~20 min average × 4 weeks = ~400 minutes/month
- OpenAI Whisper: 400 × $0.006 = ~$2.40/month
- Railway hobby tier: ~$5/month
- **Total expected:** ~$7.40/month, well within $10 ceiling.

**Audio file size projection (Whisper 25MB limit):**
- 30 min audio at 64 kbps MP3 ≈ 14 MB (fits comfortably)
- 60 min audio at 64 kbps MP3 ≈ 28 MB (requires chunking)
- 90+ min audio: chunking mandatory.

**Source coverage validation:**
- `yt-dlp` officially supports: YouTube, Instagram (Reels/posts/stories with cookie), TikTok, Vimeo, Twitter/X, Facebook, Twitch, generic HTML pages with `<video>` tags and various embedded players (1000+ extractors total).

### B. Stakeholder Input

**Stakeholder:** Project Owner (Andre)

**Confirmed decisions:**
- Hosting platform: **Railway** (confirmed)
- Cost protection strategy: **OpenAI account spending cap** (confirmed)
- Volume profile: **~5 vídeos/week, mostly ≤60 min, single-user-at-a-time** (confirmed)
- Target language: **PT-BR primary** (confirmed)
- Authentication: **None at MVP** (confirmed — public URL shared with trusted circle)

**Pending decisions:**
- Frontend framework choice (Streamlit / Gradio / custom)
- Hard length cap on input videos (60 min limit yes/no) = YES (validated by user)
- Sync vs. async backend architecture

### C. References

- OpenAI Whisper API documentation: https://platform.openai.com/docs/guides/speech-to-text
- yt-dlp project: https://github.com/yt-dlp/yt-dlp
- Railway deployment docs: https://docs.railway.app
- Streamlit: https://streamlit.io/
- Gradio: https://www.gradio.app/

---

## Next Steps

### Immediate Actions

1. Owner reviews and approves this brief, confirms working name or proposes alternative.
2. Owner answers Open Questions (especially: frontend framework choice, length cap, sync/async).
3. Hand off to **@pm (Morgan)** for PRD generation — translate this brief into a complete Product Requirements Document with detailed FR-* / NFR-* / CON-* requirements.
4. **@architect (Aria)** subsequently produces technical architecture document covering: deployment topology, request flow, error handling strategy, audio chunking approach, secrets management.
5. **@sm (River)** drafts the first user-facing story (likely "URL input → transcription happy path").
6. Set OpenAI account hard spending limit to $20/month before any code is deployed (manual stakeholder action).

### PM Handoff

This Project Brief provides the full context for **Transcrição Universal**.

@pm — Please start in 'PRD Generation Mode'. Review the brief thoroughly and work with the user to create the PRD section by section as the template indicates. Pay particular attention to:

- **Unresolved decisions** flagged in Open Questions (sync vs async, length cap, frontend choice) — these belong in the PRD as explicit requirements.
- **Risk mitigation strategies** flagged in Key Risks — convert to NFR-* (non-functional requirements) where appropriate (e.g., NFR-COST-CAP, NFR-SOURCE-RESILIENCE).
- **MVP scope discipline** — resist adding Phase 2 features (history, password gate, multilingual) into the MVP without explicit user buy-in.
- Constitutional Article IV (No Invention) — every PRD requirement must trace back to a statement in this brief or an explicit user clarification. Flag and ask for any expansion.

Ask the user for clarification on the Pending decisions in Appendix B before finalizing the PRD.
