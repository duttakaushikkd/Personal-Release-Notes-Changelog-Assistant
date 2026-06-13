"""Streamlit UI entrypoint moved into backend package."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from backend.chunking.chunking import start as chunk_start
from backend.retrieval.retrieval import retrieve
from backend.generation.generation import generate_release_notes

st.set_page_config(page_title="Release Notes Assistant", layout="wide")

st.title("Personal Release Notes — Changelog Assistant")

tabs = st.tabs(["Upload & Chunk", "Query & Generate"])

with tabs[0]:
    st.header("1) Upload a document to chunk")
    uploaded = st.file_uploader("Upload PDF or text file", type=["pdf", "txt", "md"])
    outdir = Path("uploads")
    outdir.mkdir(exist_ok=True)

    if uploaded is not None:
        save_path = outdir / uploaded.name
        with open(save_path, "wb") as f:
            f.write(uploaded.getbuffer())
        st.success(f"Saved uploaded file to {save_path}")

        st.info("Starting chunking — this may take a while for large PDFs...")
        chunks = chunk_start(str(save_path))
        if chunks is None:
            st.error("Chunking failed — check the server logs for details")
        else:
            st.success(f"Chunking complete: wrote {len(chunks)} chunks to data/chunks.json")
            if len(chunks) > 0:
                st.write("Preview of first chunk:")
                st.text_area("chunk0", chunks[0]["text"][:4000], height=200)

with tabs[1]:
    st.header("2) Query your chunks and generate release notes")
    query = st.text_input("Enter your query", value="Summarize user-visible changes")
    topk = st.number_input("Top-k retrieval", min_value=1, max_value=20, value=5)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Retrieve"):
            try:
                results = retrieve(query, top_k=topk, data_path="data/chunks.json")
                st.write(f"Top {len(results)} results:")
                for r in results:
                    st.markdown(f"**score={r['score']:.4f} id={r.get('id')}**")
                    st.write(r.get("text")[:1000])
            except Exception as e:
                st.error(f"Retrieval failed: {e}")
    with col2:
        if st.button("Generate Release Notes"):
            try:
                results = retrieve(query, top_k=topk, data_path="data/chunks.json")
                notes = generate_release_notes(query, results)
                st.subheader("Generated Release Notes")
                st.write(notes)
            except Exception as e:
                st.error(f"Generation failed: {e}")

    st.markdown("---")
    st.markdown("Use the Upload tab to add a document first. If you run embeddings via Ollama, the generator may produce richer output.")

