import os
import argparse
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

def chunking(pdf_path: str = "sample.pdf"):
    """Chunk the provided PDF and return the created Chroma vector store.

    Args:
        pdf_path: path to the PDF file to load (defaults to 'sample.pdf').

    Returns:
        The Chroma vector store instance containing the embedded chunks, or None
        if the file is missing.
    """
    print("Loading document...")
    # Check provided PDF path
    if not os.path.exists(pdf_path):
        print(f"Please place '{pdf_path}' file in the directory or update the path.")
        return None

    # Quick magic check: if the file doesn't start with the PDF magic header
    # '%PDF-' then treat it as a plain text file to avoid Pdf parsing errors.
    try:
        with open(pdf_path, "rb") as fh:
            header = fh.read(5)
    except Exception as e:
        print("Unable to open file:", e)
        return None

    if header != b"%PDF-":
        print("File does not appear to be a PDF (magic header mismatch). Reading as text...")
        try:
            with open(pdf_path, "r", encoding="utf-8", errors="replace") as tf:
                text = tf.read()
        except Exception as e:
            print("Failed to read file as text:", e)
            return None

        # Create a minimal Document-like object with `page_content` so the
        # existing splitter code can operate unchanged.
        class _SimpleDoc:
            def __init__(self, text):
                self.page_content = text

        docs = [_SimpleDoc(text)]
    else:
        loader = PyPDFLoader(pdf_path)
        try:
            docs = loader.load()
        except Exception as e:
            print("PDF loader failed, attempting to read as text. Error:", e)
            try:
                with open(pdf_path, "r", encoding="utf-8", errors="replace") as tf:
                    text = tf.read()
            except Exception as e2:
                print("Failed to read file as text after PDF loader failed:", e2)
                return None

            class _SimpleDoc:
                def __init__(self, text):
                    self.page_content = text

            docs = [_SimpleDoc(text)]

    print("Chunking document into smaller pieces...")
    # Split text into manageable sizes with an overlap to maintain context between chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = text_splitter.split_documents(docs)

    print("Initializing embedding model and vector database...")
    # Local embedding model via Ollama
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Store chunks into an in-memory Chroma vector database
    vector_store = Chroma.from_documents(documents=chunks, embedding=embeddings)

    # Return the in-memory vector store so callers can use it for retrieval or
    # persistence if desired.
    return vector_store


def start(pdf_path: str = "sample.pdf"):
    """Convenience wrapper to start the chunking pipeline.

    Use this from other modules or call via the command-line entrypoint.
    """
    return chunking(pdf_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run chunking pipeline on a PDF")
    parser.add_argument("--pdf", default="changelog.pdf", help="Path to PDF (default: sample.pdf)")
    args = parser.parse_args()
    start(args.pdf)

