"""Streamlit entry point — full pipeline UI.

Story 1.2: URL validation + metadata fetch.
Story 1.3: audio download + tempfile cleanup + NFR10-safe logging.
Story 1.4: Whisper transcription (single-call + chunked) + retries.
Story 1.5: result rendering + MM:SS duration line + Copiar button.
           Input is wrapped in st.form(clear_on_submit=True) per AC7
           (literal interpretation: input cleared after each submit).
"""

import json
import logging
import shutil
import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from app.duration import format_duration
from app.errors import TranscricaoError, UnexpectedError
from app.extractor import download_audio, fetch_metadata
from app.logging_config import hash_url, setup_logging
from app.transcriber import assert_api_key_configured, transcribe
from app.url_validation import validate_url

# Idempotent — Streamlit reruns this module on every interaction.
setup_logging()

# AC9 (Story 1.4): fail fast at app startup if OPENAI_API_KEY is missing.
assert_api_key_configured()

logger = logging.getLogger(__name__)


def _render_copiar_button(text: str) -> None:
    """Render a 'Copiar' button that copies `text` to the user's clipboard.

    Uses minimal JS injection because Streamlit (as of v1.40) lacks a
    native clipboard component. The 'Copiado!' toast persists for ~2 s
    via setTimeout (PRD AC6).

    Security: `text` is JSON-escaped via `json.dumps` before embedding in
    JS to prevent XSS even on adversarial transcripts.
    """
    escaped = json.dumps(text)  # safe JSON-escaping for embedding in JS
    html = f"""
    <button id="copiar-btn"
            style="padding: 8px 16px; font-size: 14px; cursor: pointer;
                   background: #ff4b4b; color: white; border: none;
                   border-radius: 4px;">
        Copiar
    </button>
    <span id="copy-status" style="margin-left: 12px; color: #28a745;
                                   font-weight: 600;"></span>
    <script>
      const btn = document.getElementById('copiar-btn');
      const statusEl = document.getElementById('copy-status');
      btn.addEventListener('click', async () => {{
        try {{
          await navigator.clipboard.writeText({escaped});
          statusEl.textContent = 'Copiado!';
          setTimeout(() => {{ statusEl.textContent = ''; }}, 2000);
        }} catch (err) {{
          statusEl.textContent = 'Falha ao copiar';
          statusEl.style.color = '#d33';
        }}
      }});
    </script>
    """
    components.html(html, height=80)


st.set_page_config(page_title="Transcrição Universal", page_icon="🎙️")
st.title("Transcrição Universal")

# AC7 (Story 1.5): wrap input + submit in st.form with clear_on_submit=True
# so the input field is literally cleared after each successful submission,
# honoring "the input field is reset and ready" verbatim.
with st.form("transcribe_form", clear_on_submit=True):
    url_input = st.text_input(
        label="Cole aqui o link do vídeo",
        key="url_input",
        placeholder="https://...",
    )
    submitted = st.form_submit_button("Transcrever")

if submitted:
    # AC5 (Story 1.6): top-level catch-all wraps the entire pipeline. Any
    # uncaught exception below produces a graceful PT-BR message rather than
    # a Streamlit stack-trace dump. Architecture §6.3.
    try:
        try:
            url = validate_url(url_input)
        except TranscricaoError as e:
            st.error(e.user_message_pt)
            st.stop()

        with st.status("Validando vídeo...", expanded=True) as status:
            try:
                metadata = fetch_metadata(url)
            except TranscricaoError as e:
                status.update(label="Falha", state="error")
                st.error(e.user_message_pt)
                st.stop()

            status.update(label="Baixando áudio...", state="running")

            audio_dir = Path(tempfile.mkdtemp(prefix="transcricao_"))
            try:
                try:
                    audio_path = download_audio(url, target_dir=audio_dir)
                except TranscricaoError as e:
                    status.update(label="Falha", state="error")
                    st.error(e.user_message_pt)
                    st.stop()

                # AC8 (Story 1.3): single INFO log line with download metadata.
                logger.info(
                    "download_ok url_hash=%s source=%s duration_s=%d file_size_bytes=%d",
                    hash_url(url),
                    metadata.source_domain,
                    metadata.duration_seconds,
                    audio_path.stat().st_size,
                )

                status.update(label="Transcrevendo...", state="running")

                try:
                    transcript = transcribe(audio_path, metadata.duration_seconds)
                except TranscricaoError as e:
                    status.update(label="Falha", state="error")
                    st.error(e.user_message_pt)
                    st.stop()

                # AC8-equivalent for transcription stage. NFR10: ONLY length is
                # logged; transcript content is NEVER emitted to logs.
                logger.info(
                    "transcription_ok url_hash=%s source=%s duration_s=%d transcript_chars=%d",
                    hash_url(url),
                    metadata.source_domain,
                    metadata.duration_seconds,
                    len(transcript),
                )

                status.update(label="Pronto", state="complete")

                # === STORY 1.5 RENDERING ===
                # AC1, AC2: render transcript as scrollable, selectable text area.
                # No timestamps/speakers/markers — Whisper returns plain text already.
                st.text_area(
                    label="Transcrição (PT-BR)",
                    value=transcript,
                    height=400,
                    key="transcript_output",
                )

                # AC3, AC4: duration line uses metadata.duration_seconds (NOT recomputed).
                duration_line = f"Duração total: {format_duration(metadata.duration_seconds)}"
                st.markdown(f"**{duration_line}**")

                # AC5, AC6: "Copiar" button copies transcript + duration line.
                full_copy_text = f"{transcript}\n\n{duration_line}"
                _render_copiar_button(full_copy_text)
            finally:
                # AC7 (Story 1.3): cleanup happens whether transcription succeeds
                # or fails. Container restart on Railway also wipes /tmp.
                shutil.rmtree(audio_dir, ignore_errors=True)
    except TranscricaoError:
        # Defensive: every TranscricaoError above is caught at its stage
        # boundary and short-circuited via st.stop(). This branch is a no-op
        # safety net for any subclass that somehow bubbles past the inner
        # handlers (should not happen).
        pass
    except Exception:
        # AC4 (Story 1.6): full traceback to stdout (URL redacted by SafeLogFilter).
        # AC5: show generic PT-BR message — no stack trace to user.
        # NOTE (PO INFO-1): This does NOT catch st.stop() — StopException is
        # BaseException in Streamlit 1.40+, so per-stage st.stop() calls
        # bubble up correctly to Streamlit's runner.
        logger.exception("Unexpected error in pipeline")
        st.error(UnexpectedError().user_message_pt)
