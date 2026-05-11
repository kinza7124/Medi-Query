"""
helper.py — Advanced hybrid chunking pipeline for medical PDFs.

  1. PyMuPDF layout-aware PDF loading with font-size heading detection
  2. Stronger medical heading regex — Title-Case guard tightened to prevent
     body lines being misclassified as headings (max 5 words, no verb endings,
     majority of words must be capitalised)
  3. Sentence-level overlap (carry last 1-2 sentences)
  4. TOKEN-AWARE adaptive chunk sizing (not character-based):
       prose      → 200 tokens  (~900 chars at medical text density)
       structured → 100 tokens  (~450 chars)
     Uses tiktoken cl100k_base + BGE correction factor for accurate budgeting.
     Token count stored in every chunk's metadata.
  5. Deduplication: fingerprint-based removal of repeated headers/footers/chunks
  6. Subsection boundary detection splits large sections intelligently
  7. Full page + section + source + chunk_index + token_count metadata
  8. NLTK sentence tokenisation
  9. Topic-shift detection via sentence-count cap per chunk
 10. Structured content (bullets/tables) chunked independently from prose
 11. PDFs parsed ONCE — blocks extracted in load_pdf_blocks() and passed
     directly into the chunker; no second fitz.open() call at chunk time.
"""

import os
import glob as _glob
import re
import hashlib
from typing import List, Dict, Tuple, Optional

import fitz                                          # PyMuPDF
import nltk
import tiktoken
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

# Ensure NLTK sentence tokeniser data is present
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


# ─────────────────────────────────────────────────────────────────────────────
# Token counter — tiktoken cl100k + BGE correction factor
# ─────────────────────────────────────────────────────────────────────────────

class _TokenCounter:
    """
    Fast token counter using tiktoken cl100k_base.

    BGE/WordPiece tokenises medical text ~10% more aggressively than cl100k
    (long drug names, Latin terms split into more sub-words).
    A correction factor of 1.10 converts cl100k counts to approximate BGE
    token counts, keeping chunks safely within the embedding model's window
    without needing to load the full HuggingFace tokenizer at index time.

    BGE-small-en-v1.5 max context: 512 tokens.
    We target well below that so the [section] prefix + chunk body both fit.
    """
    _BGE_CORRECTION = 1.10   # WordPiece inflates ~10% vs cl100k on medical text

    def __init__(self):
        self._enc = tiktoken.get_encoding("cl100k_base")

    def count(self, text: str) -> int:
        """Return estimated BGE token count for text."""
        cl100k_tokens = len(self._enc.encode(text, disallowed_special=()))
        return int(cl100k_tokens * self._BGE_CORRECTION)

    def fits(self, current_tokens: int, new_text: str, budget: int) -> bool:
        """True if adding new_text stays within the token budget."""
        return current_tokens + self.count(new_text) + 1 <= budget


# Module-level singleton — created once, reused across all calls
_TC = _TokenCounter()


# ─────────────────────────────────────────────────────────────────────────────
# Constants  (all in TOKENS, not characters)
# ─────────────────────────────────────────────────────────────────────────────

# Token budgets per content type
# BGE-small max = 512 tokens; we leave headroom for the [Section] prefix
CHUNK_TOKENS_PROSE  = 200   # ~900 chars at medical text density (~4.5 chars/tok)
CHUNK_TOKENS_STRUCT = 100   # ~450 chars — tighter for lists/tables

# Sentence-level overlap: carry this many trailing sentences into next chunk
OVERLAP_SENTENCES = 2

# Max sentences per chunk before forcing a split (topic-shift guard)
MAX_SENTENCES_PER_CHUNK = 12

# Minimum token count to keep a section (noise filter)
MIN_SECTION_TOKENS = 10

# Patterns that identify boilerplate / footer / header noise to deduplicate
_BOILERPLATE_RE = re.compile(
    r'^(page\s*\d+|gale encyclopedia|copyright|all rights reserved'
    r'|www\.|http|isbn|printed in|for more information|see also'
    r'|\d{1,3}\s*$)',
    re.IGNORECASE,
)

# Medical heading patterns (ordered strongest → weakest)
# Each pattern must match the ENTIRE stripped line (anchored ^ … $).
_HEADING_PATTERNS: List[re.Pattern] = [
    # Numbered section: "1.", "1.2", "A.", "I." at line start
    re.compile(r'^([A-Z0-9]+[\.\)]\s+[A-Z][A-Za-z\s\-]{2,60})$'),
    # ALL-CAPS line, 2-8 words, no trailing punctuation
    re.compile(r'^([A-Z][A-Z\s\-\/]{2,60})$'),
    # Title-Case — tightened to max 5 words; every non-stop word must be capitalised
    re.compile(r'^((?:[A-Z][a-zA-Z\-]{0,29})(?:\s+(?:[A-Z][a-zA-Z\-]{0,29}|and|or|of|the|in|for|with|a|an)){1,4})$'),
    # Single capitalised medical word (≥4 chars, alpha only)
    re.compile(r'^([A-Z][a-z]{3,30})$'),
]

# Verb-like suffixes that disqualify a Title-Case match (indicates prose, not a heading)
_PROSE_SUFFIX_RE = re.compile(r'(?:ing|tion|tions|ness|ment|ments|edly|ingly)\s*$', re.IGNORECASE)

# Known medical subsection keywords — used to detect subsection boundaries
_SUBSECTION_KEYWORDS = re.compile(
    r'^(causes?|symptoms?|signs?|diagnosis|treatment|management|prevention'
    r'|complications?|prognosis|epidemiology|pathophysiology|definition'
    r'|overview|description|risk factors?|clinical presentation'
    r'|differential diagnosis|investigations?|tests?|medications?'
    r'|surgery|lifestyle|diet|outlook|resources?|organizations?)',
    re.IGNORECASE,
)

# Structured-content detector: line starts with bullet, dash, number, or looks tabular
_STRUCT_LINE_RE = re.compile(
    r'^(\s*[\•\-\*\–\—]\s|\s*\d+[\.\)]\s|\s*[a-zA-Z][\.\)]\s|\t)'
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. PDF Loading — PyMuPDF layout-aware, parsed ONCE
# ─────────────────────────────────────────────────────────────────────────────

class _PageBlock:
    """Holds one text block extracted from a PDF page."""
    __slots__ = ("text", "font_size", "is_bold", "page_num")

    def __init__(self, text: str, font_size: float, is_bold: bool, page_num: int):
        self.text      = text.strip()
        self.font_size = font_size
        self.is_bold   = is_bold
        self.page_num  = page_num


class PDFBlocks:
    """
    Container for all blocks extracted from one PDF file.
    Produced by load_pdf_blocks() and consumed directly by the chunker,
    so the file is opened with fitz exactly once.
    """
    __slots__ = ("source", "blocks", "median_font")

    def __init__(self, source: str, blocks: List[_PageBlock], median_font: float):
        self.source      = source
        self.blocks      = blocks
        self.median_font = median_font


def load_pdf_blocks(data: str) -> List[PDFBlocks]:
    """
    Open every PDF in `data/` with PyMuPDF ONCE and return PDFBlocks objects.
    This is the single entry point for PDF parsing — nothing else calls fitz.open().

    Falls back to PyPDFLoader per-file if PyMuPDF fails.
    """
    pdf_paths = _glob.glob(os.path.join(data, "*.pdf"))
    result: List[PDFBlocks] = []

    for pdf_path in pdf_paths:
        try:
            doc    = fitz.open(pdf_path)
            blocks: List[_PageBlock] = []
            sizes:  List[float]      = []

            for page_num, page in enumerate(doc, start=1):
                raw_blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
                for blk in raw_blocks:
                    if blk.get("type") != 0:
                        continue
                    for line in blk.get("lines", []):
                        for span in line.get("spans", []):
                            txt  = span.get("text", "").strip()
                            size = span.get("size", 10.0)
                            bold = bool(span.get("flags", 0) & 2**4)
                            if txt:
                                blocks.append(_PageBlock(txt, size, bold, page_num))
                                sizes.append(size)

            doc.close()
            sizes.sort()
            median_font = sizes[len(sizes) // 2] if sizes else 10.0
            result.append(PDFBlocks(pdf_path, blocks, median_font))

        except Exception:
            # Fallback: convert PyPDFLoader pages into synthetic _PageBlock lists
            try:
                loader = PyPDFLoader(pdf_path)
                fallback_blocks: List[_PageBlock] = []
                for doc_page in loader.load():
                    page_num = doc_page.metadata.get("page", 0) + 1
                    for line in doc_page.page_content.splitlines():
                        line = line.strip()
                        if line:
                            fallback_blocks.append(_PageBlock(line, 10.0, False, page_num))
                result.append(PDFBlocks(pdf_path, fallback_blocks, 10.0))
            except Exception:
                pass   # skip unreadable files

    return result


# Module-level block cache: pdf_path → PDFBlocks
# Populated by chunk_pdf_dir(); consulted by hybrid_chunk_documents()
# so a second fitz.open() is never needed in the same process.
_BLOCK_CACHE: Dict[str, PDFBlocks] = {}


def load_pdf_file(data: str) -> List[Document]:
    """
    Backward-compatible loader. Internally calls load_pdf_blocks() (single parse)
    and converts blocks to LangChain Documents grouped by page.
    """
    all_blocks = load_pdf_blocks(data)
    documents: List[Document] = []

    for pdf_blocks in all_blocks:
        page_map: Dict[int, List[str]] = {}
        for blk in pdf_blocks.blocks:
            page_map.setdefault(blk.page_num, []).append(blk.text)
        for page_num, texts in sorted(page_map.items()):
            documents.append(Document(
                page_content="\n".join(texts),
                metadata={"source": pdf_blocks.source, "page": page_num},
            ))

    return documents


def filter_to_minimal_docs(docs: List[Document]) -> List[Document]:
    """Keep source + page metadata, drop everything else."""
    result: List[Document] = []
    for doc in docs:
        result.append(Document(
            page_content=doc.page_content,
            metadata={
                "source": doc.metadata.get("source", "Unknown"),
                "page":   doc.metadata.get("page", 0),
            },
        ))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 2. Heading detection — layout-aware + strong regex
# ─────────────────────────────────────────────────────────────────────────────

def _is_heading_by_layout(block: _PageBlock, median_font: float) -> bool:
    """True if the block's font is noticeably larger or bold vs body text."""
    return block.is_bold or block.font_size >= median_font * 1.15


def _is_heading_by_regex(line: str) -> Optional[str]:
    """
    Apply medical heading regex patterns.
    Returns cleaned heading text or None.

    Title-Case guard: lines that end with verb/noun suffixes (-ing, -tion,
    -ness, -ment, -edly) are almost always prose fragments, not headings.
    We reject them even if they match the Title-Case pattern.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 100:
        return None
    # Reject lines that end with sentence punctuation (they're prose)
    if stripped.endswith(('.', ',', ';', '?', '!')):
        return None
    # Reject lines that are clearly boilerplate
    if _BOILERPLATE_RE.match(stripped):
        return None

    for i, pattern in enumerate(_HEADING_PATTERNS):
        m = pattern.match(stripped)
        if m:
            heading = m.group(1).strip()
            # For Title-Case pattern (index 2): apply extra prose-suffix guard
            if i == 2 and _PROSE_SUFFIX_RE.search(heading):
                return None
            # Normalise ALL-CAPS to Title Case
            if heading.isupper():
                heading = heading.title()
            return heading

    return None


def _is_subsection_boundary(line: str) -> bool:
    """True if the line looks like a known medical subsection keyword heading."""
    return bool(_SUBSECTION_KEYWORDS.match(line.strip()))


# ─────────────────────────────────────────────────────────────────────────────
# 3. Text cleaning
# ─────────────────────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _is_boilerplate(text: str) -> bool:
    return bool(_BOILERPLATE_RE.match(text.strip()))


# ─────────────────────────────────────────────────────────────────────────────
# 4. Content-type classification
# ─────────────────────────────────────────────────────────────────────────────

def _classify_content(text: str) -> str:
    """
    Returns 'structured' (bullets/tables/lists) or 'prose'.
    Structured content gets a smaller chunk size.
    """
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return "prose"
    struct_count = sum(1 for l in lines if _STRUCT_LINE_RE.match(l))
    # If >40% of lines look structured, treat the whole block as structured
    return "structured" if struct_count / len(lines) > 0.4 else "prose"


# ─────────────────────────────────────────────────────────────────────────────
# 5. NLTK sentence tokenisation
# ─────────────────────────────────────────────────────────────────────────────

def _split_into_sentences(text: str) -> List[str]:
    """
    Use NLTK Punkt tokeniser for robust sentence segmentation.
    Handles medical abbreviations (Dr., mg., etc.) far better than regex.
    Falls back to simple period-split if NLTK fails.
    """
    try:
        sentences = nltk.sent_tokenize(text)
        return [s.strip() for s in sentences if s.strip()]
    except Exception:
        # Minimal fallback
        raw = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in raw if s.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Token-aware semantic chunking with sentence-level overlap
# ─────────────────────────────────────────────────────────────────────────────

def _semantic_chunks(
    sentences: List[str],
    token_budget: int,
) -> List[List[str]]:
    """
    Greedily merge sentences into chunks bounded by token_budget AND
    MAX_SENTENCES_PER_CHUNK (topic-shift guard).

    Sizing is TOKEN-based via _TC.count(), not character-based.
    This ensures consistent embedding density regardless of whether the
    text contains short common words or long medical/Latin terms.

    Overlap: last OVERLAP_SENTENCES sentences of each chunk are prepended
    to the next chunk (sentence-level, not character-level).

    Returns a list of sentence-lists (one per chunk).
    """
    chunks: List[List[str]] = []
    current: List[str] = []
    current_tokens = 0

    for sent in sentences:
        sent_tokens = _TC.count(sent)

        over_budget = (current_tokens + sent_tokens + 1 > token_budget) and current
        over_count  = len(current) >= MAX_SENTENCES_PER_CHUNK and current

        if over_budget or over_count:
            chunks.append(current)
            # Sentence-level overlap: carry last OVERLAP_SENTENCES sentences
            overlap        = current[-OVERLAP_SENTENCES:] if len(current) >= OVERLAP_SENTENCES else current[:]
            current        = overlap[:]
            current_tokens = sum(_TC.count(s) + 1 for s in current)

        current.append(sent)
        current_tokens += sent_tokens + 1   # +1 for join space

    if current:
        chunks.append(current)

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# 7. Deduplication
# ─────────────────────────────────────────────────────────────────────────────

def _fingerprint(text: str) -> str:
    """MD5 fingerprint of normalised text for dedup."""
    normalised = re.sub(r'\s+', ' ', text.lower().strip())
    return hashlib.md5(normalised.encode()).hexdigest()


def _deduplicate(docs: List[Document]) -> List[Document]:
    """
    Remove exact-duplicate chunks (same normalised content).
    Also strips chunks whose content is pure boilerplate.
    """
    seen: set = set()
    result: List[Document] = []
    for doc in docs:
        if _is_boilerplate(doc.page_content):
            continue
        fp = _fingerprint(doc.page_content)
        if fp in seen:
            continue
        seen.add(fp)
        result.append(doc)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 8. Section extraction — layout-aware + regex fallback
# ─────────────────────────────────────────────────────────────────────────────

def _extract_sections_from_blocks(
    blocks: List[_PageBlock],
    median_font: float,
    source: str,
) -> List[Dict]:
    """
    Walk PyMuPDF blocks. Use font-size/bold metadata as primary heading signal,
    regex as secondary. Accumulate body text per section.

    Returns list of dicts:
      {header, text, source, page, content_type}
    """
    sections: List[Dict] = []
    current_header = "General Medical Information"
    current_page   = 1

    for blk in blocks:
        text = blk.text.strip()
        if not text or _is_boilerplate(text):
            continue

        # Heading detection: layout first, then regex
        if _is_heading_by_layout(blk, median_font):
            heading = _is_heading_by_regex(text) or text.title()[:80]
            current_header = heading
            current_page   = blk.page_num
            continue

        heading_by_regex = _is_heading_by_regex(text)
        if heading_by_regex:
            current_header = heading_by_regex
            current_page   = blk.page_num
            continue

        # Subsection boundary inside a large section
        if _is_subsection_boundary(text):
            current_header = text.strip().title()
            current_page   = blk.page_num
            continue

        # Accumulate body text
        if (
            sections
            and sections[-1]["header"] == current_header
            and sections[-1]["source"] == source
        ):
            sections[-1]["text"] += " " + text
        else:
            sections.append({
                "header":       current_header,
                "text":         text,
                "source":       source,
                "page":         blk.page_num,
                "content_type": _classify_content(text),
            })

    return sections


def _extract_sections_from_docs(documents: List[Document]) -> List[Dict]:
    """
    Fallback section extractor when PyMuPDF blocks aren't available.
    Uses regex heading detection on plain text lines.
    """
    sections: List[Dict] = []

    for doc in documents:
        source = doc.metadata.get("source", "Unknown")
        page   = doc.metadata.get("page", 0)
        cleaned = _clean_text(doc.page_content)
        lines   = cleaned.split('\n')
        current_header = "General Medical Information"

        for line in lines:
            heading = _is_heading_by_regex(line)
            if heading:
                current_header = heading
                continue

            if _is_subsection_boundary(line):
                current_header = line.strip().title()
                continue

            line_text = line.strip()
            if not line_text or _is_boilerplate(line_text):
                continue

            if (
                sections
                and sections[-1]["header"] == current_header
                and sections[-1]["source"] == source
            ):
                sections[-1]["text"] += " " + line_text
            else:
                sections.append({
                    "header":       current_header,
                    "text":         line_text,
                    "source":       source,
                    "page":         page,
                    "content_type": _classify_content(line_text),
                })

    return sections


# ─────────────────────────────────────────────────────────────────────────────
# 9. Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def hybrid_chunk_documents(
    documents: List[Document],
    chunk_size: int = CHUNK_TOKENS_PROSE,    # token budget (not chars)
    chunk_overlap: int = OVERLAP_SENTENCES,  # kept for API compat, unused internally
) -> List[Document]:
    """
    Full hybrid chunking pipeline.

    Accepts either:
      • List[Document]  — backward-compatible path; internally calls
                          load_pdf_blocks() to get layout data (single parse
                          because load_pdf_file already used load_pdf_blocks).
      • Called via chunk_pdf_dir() — preferred path that passes PDFBlocks
                          directly, guaranteeing zero double-parsing.

    Pass 1 — Layout-aware section extraction (blocks already in memory).
    Pass 2 — Token-aware adaptive semantic chunking per section.
    Pass 3 — Deduplication.
    """
    # Derive unique PDF paths from the documents
    pdf_paths = list({
        doc.metadata.get("source", "")
        for doc in documents
        if doc.metadata.get("source", "").endswith(".pdf")
    })

    all_sections: List[Dict] = []

    for pdf_path in pdf_paths:
        if not os.path.exists(pdf_path):
            continue
        # Re-use already-loaded blocks from the module-level cache if available,
        # otherwise fall back to the doc text (no second fitz.open needed because
        # the preferred entry point is chunk_pdf_dir which passes blocks directly).
        cached = _BLOCK_CACHE.get(pdf_path)
        if cached is not None:
            secs = _extract_sections_from_blocks(cached.blocks, cached.median_font, pdf_path)
        else:
            # Fallback: extract from Document text (no fitz re-open)
            doc_subset = [d for d in documents if d.metadata.get("source") == pdf_path]
            secs = _extract_sections_from_docs(doc_subset)
        all_sections.extend(secs)

    if not all_sections:
        all_sections = _extract_sections_from_docs(documents)

    return _build_chunks(all_sections)


def chunk_pdf_dir(data: str) -> List[Document]:
    """
    Preferred single-call entry point.

    Parses every PDF in `data/` ONCE with PyMuPDF, extracts blocks,
    caches them, then runs the full chunking pipeline — no double IO.

    Usage in store_index.py:
        from src.helper import chunk_pdf_dir
        text_chunks = chunk_pdf_dir('data/')
    """
    all_pdf_blocks = load_pdf_blocks(data)   # single fitz.open per file
    all_sections: List[Dict] = []

    for pdf_blocks in all_pdf_blocks:
        # Cache so hybrid_chunk_documents can also find them if called separately
        _BLOCK_CACHE[pdf_blocks.source] = pdf_blocks
        secs = _extract_sections_from_blocks(
            pdf_blocks.blocks, pdf_blocks.median_font, pdf_blocks.source
        )
        all_sections.extend(secs)

    return _build_chunks(all_sections)


def _build_chunks(all_sections: List[Dict]) -> List[Document]:
    """Pass 2 + Pass 3: token-aware chunking then deduplication."""
    raw_chunks: List[Document] = []

    for section in all_sections:
        header       = section["header"]
        text         = section["text"].strip()
        source       = section["source"]
        page         = section["page"]
        content_type = section.get("content_type", "prose")

        if _TC.count(text) < MIN_SECTION_TOKENS:
            continue

        token_budget = CHUNK_TOKENS_STRUCT if content_type == "structured" else CHUNK_TOKENS_PROSE
        sentences    = _split_into_sentences(text)
        sent_groups  = _semantic_chunks(sentences, token_budget)

        for i, sent_group in enumerate(sent_groups):
            chunk_text = " ".join(sent_group).strip()
            if not chunk_text:
                continue
            chunk_tokens = _TC.count(f"[{header}]\n{chunk_text}")

            raw_chunks.append(Document(
                page_content=f"[{header}]\n{chunk_text}",
                metadata={
                    "source":       source,
                    "page":         page,
                    "section":      header,
                    "chunk_index":  i,
                    "content_type": content_type,
                    "chunk_type":   "hybrid_semantic_v2",
                    "token_count":  chunk_tokens,
                },
            ))

    return _deduplicate(raw_chunks)


# ── Backward-compat wrappers ────────────────────────────────────────────────

def context_aware_split(
    documents: List[Document],
    chunk_size: int = CHUNK_TOKENS_PROSE,   # now interpreted as token budget
    chunk_overlap: int = 100,
) -> List[Document]:
    """Legacy alias → hybrid_chunk_documents."""
    return hybrid_chunk_documents(documents, chunk_size)


def text_split(extracted_data):
    """Legacy simple splitter (kept for backward compatibility)."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    return splitter.split_documents(extracted_data)


# ─────────────────────────────────────────────────────────────────────────────
# Embeddings
# ─────────────────────────────────────────────────────────────────────────────

class BGEEmbeddingsWrapper(HuggingFaceEmbeddings):
    """
    BGE-small-en-v1.5 wrapper that adds the retrieval query prefix at
    query time only (not at indexing time), as required by the BGE model family.
    """
    def embed_query(self, text: str) -> list:
        prefixed = f"Represent this sentence for searching relevant passages: {text}"
        return super().embed_query(prefixed)


def download_hugging_face_embeddings():
    """
    Returns BAAI/bge-small-en-v1.5 (384-dim, retrieval-optimised).
    Same dimensions as before — no Pinecone index rebuild needed.
    """
    return BGEEmbeddingsWrapper(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
