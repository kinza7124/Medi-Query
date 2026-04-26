import re
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from typing import List
from langchain_core.documents import Document


# 
#  PDF Loading ─────────────────────────────────────────────────
def load_pdf_file(data):
    """Extract data from all PDF files in a directory."""
    loader = DirectoryLoader(data, glob="*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    return documents


def filter_to_minimal_docs(docs: List[Document]) -> List[Document]:
    """
    Given a list of Document objects, return a new list of Document objects
    containing only 'source' in metadata and the original page_content.
    """
    minimal_docs: List[Document] = []
    for doc in docs:
        src = doc.metadata.get("source")
        minimal_docs.append(
            Document(
                page_content=doc.page_content,
                metadata={"source": src}
            )
        )
    return minimal_docs


# ── Context-Aware Chunking ──────────────────────────────────────

def _detect_section_header(line: str) -> str | None:
    """
    Heuristic to detect whether a line is a section/topic header in a
    medical textbook (e.g. 'Acne', 'ABDOMINAL PAIN', 'Causes and symptoms').
    Returns the cleaned header text, or None if the line is regular prose.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return None

    # All-caps lines (e.g. 'ABDOMINAL PAIN')
    if stripped.isupper() and len(stripped.split()) <= 8:
        return stripped.title()

    # Title-case short lines that don't end with common sentence punctuation
    # and contain mostly alphabetic characters (e.g. 'Causes and Symptoms')
    words = stripped.split()
    if (
        2 <= len(words) <= 8
        and not stripped.endswith(('.', ',', ';', ':'))
        and stripped[0].isupper()
        and sum(1 for w in words if w[0].isupper()) >= len(words) * 0.5
    ):
        return stripped

    # Single capitalised word that looks like a medical heading (e.g. 'Acne')
    if (
        len(words) == 1
        and stripped[0].isupper()
        and stripped.isalpha()
        and len(stripped) >= 3
    ):
        return stripped

    return None


def _clean_text(text: str) -> str:
    """Normalise whitespace while preserving paragraph breaks."""
    # Collapse multiple spaces/tabs into one
    text = re.sub(r'[^\S\n]+', ' ', text)
    # Collapse 3+ newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def context_aware_split(
    documents: List[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> List[Document]:
    """
    Context-aware chunking for medical PDF documents.

    Strategy:
    1. Clean and normalise extracted text.
    2. Detect section headers heuristically and track the current topic.
    3. Split using sentence-aware separators (paragraph → sentence → word).
    4. Prepend the current section header to each chunk so every chunk
       carries context about what medical topic it belongs to.
    5. Store the section header in metadata for traceability.

    Args:
        documents:     List of LangChain Document objects (from PyPDFLoader).
        chunk_size:    Target chunk size in characters.
        chunk_overlap: Overlap between consecutive chunks.

    Returns:
        A list of contextualised Document chunks ready for embedding.
    """

    # ── Step 1: Merge pages and extract sections ────────────────
    all_sections: List[dict] = []  # {"header": str, "text": str, "source": str}

    for doc in documents:
        source = doc.metadata.get("source", "Unknown")
        cleaned = _clean_text(doc.page_content)
        lines = cleaned.split('\n')

        current_header = "General Medical Information"

        for line in lines:
            header = _detect_section_header(line)
            if header:
                current_header = header
                continue

            line_text = line.strip()
            if not line_text:
                continue

            # Append to existing section or create new
            if all_sections and all_sections[-1]["header"] == current_header and all_sections[-1]["source"] == source:
                all_sections[-1]["text"] += "\n" + line_text
            else:
                all_sections.append({
                    "header": current_header,
                    "text": line_text,
                    "source": source,
                })

    # ── Step 2: Split each section with sentence-aware splitter ─
    splitter = RecursiveCharacterTextSplitter(
        # Priority order: paragraph break → sentence end → clause → word
        separators=["\n\n", ".\n", ". ", ";\n", "; ", ", ", " ", ""],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )

    contextualised_chunks: List[Document] = []

    for section in all_sections:
        header = section["header"]
        text = section["text"]
        source = section["source"]

        # Skip very short sections (noise)
        if len(text.strip()) < 30:
            continue

        # Split the section text
        sub_chunks = splitter.split_text(text)

        for i, chunk_text in enumerate(sub_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue

            # Prepend section header for context
            contextual_text = f"[{header}]\n{chunk_text}"

            contextualised_chunks.append(
                Document(
                    page_content=contextual_text,
                    metadata={
                        "source": source,
                        "section": header,
                        "chunk_index": i,
                    }
                )
            )

    return contextualised_chunks


# ── Legacy splitter (kept for backward compatibility) ───────────
def text_split(extracted_data):
    """Simple character-based splitting (legacy). Use context_aware_split instead."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    text_chunks = text_splitter.split_documents(extracted_data)
    return text_chunks


# ── Embeddings ──────────────────────────────────────────────────
def download_hugging_face_embeddings():
    embeddings = HuggingFaceEmbeddings(
        model_name='sentence-transformers/all-MiniLM-L6-v2'  # 384 dimensions
    )
    return embeddings