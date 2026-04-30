"""Streamlit entry point — full pipeline UI.

Story 1.2: URL validation + metadata fetch.
Story 1.3: audio download + tempfile cleanup + NFR10-safe logging.
Story 1.4: Whisper transcription (single-call + chunked) + retries.
Story 1.5 will replace the st.text_area placeholder with proper rendering.
"""

import logging
import shutil
import tempfile
from pathlib import Path

import streamlit as st

from app.errors import TranscricaoError
from app.extractor import download_audio, fetch_metadata
from app.logging_config import hash_url, setup_logging
from app.transcriber import assert_api_key_configured, transcribe
from app.url_validation import validate_url

# Idempotent — Streamlit reruns this module on every interaction.
setup_logging()

# AC9 (Story 1.4): fail fast at app startup if OPENAI_API_KEY is missing.
# Raises RuntimeError before Streamlit serves any request.
assert_api_key_configured()

logger = logging.getLogger(__name__)


st.set_page_config(page_title="Transcrição Universal", page_icon="🎙️")
st.title("Transcrição Universal")

url_input = st.text_input(
    label="Cole aqui o link do vídeo",
    key="url_input",
    placeholder="https://...",
)
submitted = st.button("Transcrever")

if submitted:
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

            # === STORY 1.5 HOOK ===
            # Story 1.5 will replace this st.text_area with the proper
            # MM:SS-formatted output + copy-to-clipboard button.
            st.text_area(
                label="Transcrição (PT-BR)",
                value=transcript,
                height=400,
            )
            st.write(f"Duração total (segundos): {metadata.duration_seconds}")
            status.update(label="Pronto", state="complete")
        finally:
            # AC7 (Story 1.3): cleanup happens whether transcription succeeds
            # or fails. Container restart on Railway also wipes /tmp.
            shutil.rmtree(audio_dir, ignore_errors=True)
