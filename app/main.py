"""Streamlit entry point — full pipeline UI (validate → metadata → download).

Story 1.2 added URL validation + metadata fetch.
Story 1.3 added audio download + tempfile cleanup + NFR10-safe logging.
Story 1.4 will replace the "Story 1.4 hook" block with Whisper transcription.
"""

import logging
import shutil
import tempfile
from pathlib import Path

import streamlit as st

from app.errors import TranscricaoError
from app.extractor import download_audio, fetch_metadata
from app.logging_config import hash_url, setup_logging
from app.url_validation import validate_url

# Idempotent — Streamlit reruns this module on every interaction.
setup_logging()
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

            # AC8: single INFO log line with duration + file size + source.
            # Emitted here (not inside download_audio) because metadata.duration_seconds
            # only lives at this scope. URL is hashed; never logged in full.
            logger.info(
                "download_ok url_hash=%s source=%s duration_s=%d file_size_bytes=%d",
                hash_url(url),
                metadata.source_domain,
                metadata.duration_seconds,
                audio_path.stat().st_size,
            )

            status.update(label="Transcrevendo...", state="running")

            # === STORY 1.4 HOOK ===
            # Story 1.4 will replace this block with Whisper transcription.
            # For Story 1.3, we just confirm the download landed.
            st.info(
                f"Áudio baixado em ephemeral storage. "
                f"Tamanho: {audio_path.stat().st_size} bytes. "
                f"Duração: {metadata.duration_seconds}s. "
                f"(Story 1.4 vai adicionar a transcrição aqui.)"
            )
            status.update(label="Pronto para próximas etapas", state="complete")
        finally:
            # AC7: cleanup happens whether transcription succeeds or fails.
            # Container restart on Railway also wipes /tmp — defense-in-depth.
            shutil.rmtree(audio_dir, ignore_errors=True)
