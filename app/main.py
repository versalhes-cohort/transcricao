"""Streamlit entry point — URL input form, validation, and metadata fetch.

Story 1.2 wires URL validation + yt-dlp metadata fetch into the UI.
Story 1.3 will replace the post-metadata placeholder with the audio download
pipeline; Stories 1.4-1.6 follow with transcription, rendering, and error
catalog expansion.
"""

import streamlit as st

from app.errors import TranscricaoError
from app.extractor import fetch_metadata
from app.url_validation import validate_url

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

        status.update(label="Preparando download...", state="running")
        # Story 1.3 will replace the line below with the actual audio download
        # pipeline. For Story 1.2, we just confirm metadata fetch succeeded.
        st.info(
            f"Vídeo válido. Duração: {metadata.duration_seconds}s · Fonte: {metadata.source_domain}"
        )
        status.update(label="Pronto para próximas etapas", state="complete")
