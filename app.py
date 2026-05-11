from functools import lru_cache
import re
import threading
import uuid

from flask import Flask, render_template, request, session
from src.helper import download_hugging_face_embeddings, chunk_pdf_dir
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain.retrievers.document_compressors import (
    CrossEncoderReranker,
    DocumentCompressorPipeline,
    LLMChainExtractor,
)
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_community.retrievers import BM25Retriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from dotenv import load_dotenv
from src.prompt import system_prompt, query_rewrite_system_prompt
import logging
import os

# ── Logging ────────────────────────────────────────────────────────────────
import sys

_file_handler   = logging.FileHandler("app.log", encoding="utf-8")
_stream_handler = logging.StreamHandler(sys.stdout)
try:
    _stream_handler.stream.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass  # Python < 3.7 fallback

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[_file_handler, _stream_handler],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

load_dotenv()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
GROQ_API_KEY     = os.environ.get('GROQ_API_KEY')

if not PINECONE_API_KEY or not GROQ_API_KEY:
    logger.error("Missing critical API keys in environment variables!")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GROQ_API_KEY"]     = GROQ_API_KEY

# Issue 2 fix: extractor is powerful but adds N LLM calls per query (one per
# reranked chunk). Gate it behind an env flag so production stays fast by
# default and it can be enabled for research / higher-quality mode.
# Set ENABLE_EXTRACTOR=1 in .env to turn on.
ENABLE_EXTRACTOR: bool = os.environ.get("ENABLE_EXTRACTOR", "0").strip() == "1"

# Issue 5 fix: cap session history to prevent unbounded cookie / memory growth.
# 20 messages = 10 exchanges, enough for multi-turn context.
MAX_HISTORY_MESSAGES = 20

_models_preloaded = False

@app.before_request
def startup_preload():
    global _models_preloaded
    if not _models_preloaded:
        _models_preloaded = True
        threading.Thread(target=preload_models, daemon=True).start()

# ── Cached singletons ──────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_embeddings():
    return download_hugging_face_embeddings()


@lru_cache(maxsize=1)
def get_docsearch():
    return PineconeVectorStore.from_existing_index(
        index_name="medical-chatbot",
        embedding=get_embeddings(),
    )


@lru_cache(maxsize=1)
def get_chunks():
    """
    Parse PDFs once (single fitz.open via chunk_pdf_dir) and cache chunks.
    Used by both BM25 and dense retrieval — identical document units.
    """
    try:
        chunks = chunk_pdf_dir('data/')
        logger.info(f"Loaded {len(chunks)} hybrid chunks for BM25 + dense retrieval.")
        return chunks
    except Exception as e:
        logger.warning(f"chunk_pdf_dir failed ({e}). BM25 will be unavailable.")
        return []


@lru_cache(maxsize=1)
def get_bm25_retriever():
    """
    Issue 1 fix: BM25 index built ONCE and cached.
    Previously BM25Retriever.from_documents() was called inside
    build_per_query_retriever() — O(n) rebuild on every request.
    Now it's a cached singleton like every other expensive object.
    """
    chunks = get_chunks()
    if not chunks:
        return None
    retriever = BM25Retriever.from_documents(chunks, k=8)
    logger.info(f"BM25 index built over {len(chunks)} chunks.")
    return retriever


@lru_cache(maxsize=1)
def get_extractor_llm():
    """
    Lightweight LLM for context extraction (only used when ENABLE_EXTRACTOR=1).
    8b-instant: fast enough for sentence-level extraction tasks.
    """
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0)


@lru_cache(maxsize=1)
def get_compressor_pipeline():
    """
    Issue 3 fix: single source of truth for the compressor pipeline.
    Previously the reranker was defined in get_retriever() AND the pipeline
    was partially duplicated in build_per_query_retriever(). Now both call
    this one cached function.

    Pipeline:
      CrossEncoderReranker  →  top 8 by relevance score
      LLMChainExtractor     →  only if ENABLE_EXTRACTOR=1

    Separating this from get_retriever() means build_per_query_retriever()
    can swap the base retriever (for metadata filtering) while reusing the
    exact same compressor — no duplication, no divergence.
    """
    reranker = CrossEncoderReranker(
        model=HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"),
        top_n=8,
    )

    if ENABLE_EXTRACTOR:
        extractor = LLMChainExtractor.from_llm(get_extractor_llm())
        pipeline  = DocumentCompressorPipeline(transformers=[reranker, extractor])
        logger.info("Compressor pipeline: reranker + LLM extractor (ENABLE_EXTRACTOR=1).")
    else:
        # Reranker-only: faster, still precise, recommended for production
        pipeline = DocumentCompressorPipeline(transformers=[reranker])
        logger.info("Compressor pipeline: reranker-only (set ENABLE_EXTRACTOR=1 to add extraction).")

    return pipeline


@lru_cache(maxsize=1)
def get_retriever():
    """
    Baseline cached retriever (unfiltered dense + BM25 + compressor pipeline).
    Used at startup preload and as the compressor source for per-query builds.
    """
    docsearch      = get_docsearch()
    dense_retriever = docsearch.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 10, "fetch_k": 20, "lambda_mult": 0.6},
    )

    bm25 = get_bm25_retriever()
    if bm25:
        base_retriever = EnsembleRetriever(
            retrievers=[bm25, dense_retriever],
            weights=[0.4, 0.6],
        )
        logger.info("Baseline retriever: BM25 + MMR dense ensemble.")
    else:
        base_retriever = dense_retriever
        logger.info("Baseline retriever: MMR dense-only (BM25 unavailable).")

    return ContextualCompressionRetriever(
        base_compressor=get_compressor_pipeline(),
        base_retriever=base_retriever,
    )


@lru_cache(maxsize=1)
def get_llm():
    """Single LLM instance shared by the RAG chain."""
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)


@lru_cache(maxsize=1)
def get_query_rewrite_chain():
    rewrite_llm    = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    rewrite_prompt = ChatPromptTemplate.from_messages([
        ("system", query_rewrite_system_prompt),
        ("human", "Chat history:\n{chat_history}\n\nUser query: {question}"),
    ])
    return rewrite_prompt | rewrite_llm | StrOutputParser()


# ── Metadata-aware retrieval ───────────────────────────────────────────────

_INTENT_SECTION_MAP: list[tuple[re.Pattern, list[str]]] = [
    (
        re.compile(r"\b(symptom|symptoms|sign|signs|present|presentation|feel|feeling|experience)\b", re.IGNORECASE),
        ["Symptoms", "Signs", "Clinical Presentation", "Signs And Symptoms",
         "Symptoms And Signs", "Clinical Features", "Manifestations"],
    ),
    (
        re.compile(r"\b(cause|causes|caused|etiology|aetiology|reason|reasons|why|origin|risk factor|risk factors)\b", re.IGNORECASE),
        ["Causes", "Cause", "Etiology", "Aetiology", "Risk Factors",
         "Pathophysiology", "Epidemiology", "Origins"],
    ),
    (
        re.compile(r"\b(treat|treated|treatment|treatments|manage|management|therapy|therapies|cure|medication|medications|drug|drugs|medicine|medicines|remedy|remedies|prescribed|prescription)\b", re.IGNORECASE),
        ["Treatment", "Treatments", "Management", "Therapy", "Medications",
         "Treatment And Management", "Medical Treatment", "Pharmacotherapy"],
    ),
    (
        re.compile(r"\b(prevent|prevention|preventing|avoid|avoidance|prophylaxis|reduce risk)\b", re.IGNORECASE),
        ["Prevention", "Prophylaxis", "Prevention And Control",
         "Preventive Measures", "Risk Reduction"],
    ),
    (
        re.compile(r"\b(diagnos\w*|test|tests|testing|detect|detection|screen|screening|investigation|investigations|workup)\b", re.IGNORECASE),
        ["Diagnosis", "Diagnostic", "Tests", "Investigations",
         "Differential Diagnosis", "Diagnostic Tests", "Screening"],
    ),
    (
        re.compile(r"\b(complication|complications|prognosis|outlook|outcome|outcomes|long.?term|consequence|consequences)\b", re.IGNORECASE),
        ["Complications", "Prognosis", "Outlook", "Long-Term Effects",
         "Outcomes", "Sequelae"],
    ),
    (
        re.compile(r"\b(what is|define|definition|overview|describe|description|about|explain)\b", re.IGNORECASE),
        ["Description", "Overview", "Definition", "Introduction",
         "General Medical Information", "Background"],
    ),
]


def infer_section_filter(query: str) -> dict | None:
    """Return a Pinecone $in filter for the query's intent, or None."""
    for pattern, sections in _INTENT_SECTION_MAP:
        if pattern.search(query):
            return {"section": {"$in": sections}}
    return None


def _filter_docs_by_sections(docs: list, allowed_sections: list[str]) -> list:
    """
    Issue 4 fix: post-filter BM25 results by section metadata.
    BM25Retriever has no native Pinecone-style filter, so we apply the
    same section allowlist in Python after retrieval. Docs with no section
    metadata are kept (they may be valid general content).
    """
    allowed = set(s.lower() for s in allowed_sections)
    filtered = []
    for doc in docs:
        sec = doc.metadata.get("section", "")
        if not sec or sec.lower() in allowed:
            filtered.append(doc)
    return filtered if filtered else docs   # fall back to all if filter removes everything


def build_per_query_retriever(query: str):
    """
    Issue 1 + 3 fix: per-request retriever that swaps only the dense side
    (cheap — just search_kwargs dict) while reusing all cached heavy objects:
      - BM25 index          → get_bm25_retriever()   (cached)
      - compressor pipeline → get_compressor_pipeline() (cached)

    Issue 4 fix: BM25 results are post-filtered by the same section allowlist
    applied to the dense retriever, keeping both sides consistent.
    """
    section_filter = infer_section_filter(query)
    docsearch      = get_docsearch()

    if section_filter:
        logger.info(f"Metadata filter applied: {section_filter['section']['$in']}")

    # Dense retriever: apply Pinecone metadata filter if intent detected
    if section_filter:
        logger.info(f"Metadata filter: {section_filter}")
        dense_retriever = docsearch.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 10, "fetch_k": 20, "lambda_mult": 0.6,
                "filter": section_filter,
            },
        )
    else:
        dense_retriever = docsearch.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 10, "fetch_k": 20, "lambda_mult": 0.6},
        )

    # BM25 retriever: reuse cached index, post-filter by section in Python
    bm25 = get_bm25_retriever()
    if bm25:
        if section_filter:
            allowed_sections = section_filter["section"]["$in"]

            # EnsembleRetriever requires all retrievers to be LangChain Runnable
            # instances. A plain Python class fails pydantic validation.
            # Fix: subclass BaseRetriever which satisfies the Runnable protocol.
            from langchain_core.retrievers import BaseRetriever
            from langchain_core.documents import Document as LCDocument
            from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun

            class _FilteredBM25Retriever(BaseRetriever):
                """BM25 wrapper with Python-side section post-filtering."""
                class Config:
                    arbitrary_types_allowed = True

                _bm25: object
                _allowed: list

                def __init__(self, bm25_ret, allowed_secs):
                    super().__init__()
                    object.__setattr__(self, '_bm25', bm25_ret)
                    object.__setattr__(self, '_allowed', allowed_secs)

                def _get_relevant_documents(
                    self, query: str, *, run_manager: CallbackManagerForRetrieverRun
                ) -> list[LCDocument]:
                    docs = self._bm25.invoke(query)
                    return _filter_docs_by_sections(docs, self._allowed)

            base_retriever = EnsembleRetriever(
                retrievers=[_FilteredBM25Retriever(bm25, allowed_sections), dense_retriever],
                weights=[0.4, 0.6],
            )
        else:
            base_retriever = EnsembleRetriever(
                retrievers=[bm25, dense_retriever],
                weights=[0.4, 0.6],
            )
    else:
        base_retriever = dense_retriever

    return ContextualCompressionRetriever(
        base_compressor=get_compressor_pipeline(),   # single source of truth
        base_retriever=base_retriever,
    )


# ── Request logs collector ────────────────────────────────────────────────

# ── RAG chain helpers ──────────────────────────────────────────────────────

def _format_docs(docs) -> str:
    """Concatenate retrieved docs with section + page metadata headers."""
    parts = []
    for doc in docs:
        section = doc.metadata.get("section", "")
        page    = doc.metadata.get("page", "")
        header  = f"[Section: {section} | Page: {page}]" if section else ""
        parts.append(f"{header}\n{doc.page_content}".strip())
    return "\n\n---\n\n".join(parts)


def _build_prompt(input_dict: dict) -> ChatPromptTemplate:
    formatted_system = system_prompt.format(
        chat_history=input_dict.get("chat_history", "No previous conversation."),
        context=input_dict.get("context") or "[No relevant documents found]",
        input=input_dict.get("input", ""),
    )
    return ChatPromptTemplate.from_messages([("system", formatted_system)])


def _retrieve_with_filter(x: dict) -> str:
    """Per-request retrieval: infer filter → build retriever → run → format."""
    query     = str(x.get("retrieval_query") or x.get("input", ""))
    retriever = build_per_query_retriever(query)
    docs      = retriever.invoke(query)

    logger.info(f"Retrieved {len(docs)} docs after reranking pipeline.")
    for i, doc in enumerate(docs):
        section = doc.metadata.get("section", "N/A")
        page    = doc.metadata.get("page", "?")
        preview = doc.page_content[:100].replace("\n", " ")
        logger.info(f"  Doc {i+1} | section={section} | page={page} | {preview}...")

    return _format_docs(docs)


@lru_cache(maxsize=1)
def get_rag_chain():
    llm = get_llm()
    chain = (
        RunnablePassthrough.assign(context=RunnableLambda(_retrieve_with_filter))
        | RunnableLambda(_build_prompt)
        | llm
        | StrOutputParser()
    )
    return chain


# ── Session memory ─────────────────────────────────────────────────────────

def get_session_memory():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session['chat_history'] = []
    return session['chat_history']


def update_session_memory(user_query: str, assistant_answer: str):
    """
    Issue 5 fix: cap history at MAX_HISTORY_MESSAGES to prevent unbounded
    session growth (cookie overflow or server-side memory leak).
    """
    if 'chat_history' not in session:
        session['chat_history'] = []
    session['chat_history'].append({"role": "user",      "content": user_query})
    session['chat_history'].append({"role": "assistant", "content": assistant_answer})
    # Keep only the most recent N messages
    session['chat_history'] = session['chat_history'][-MAX_HISTORY_MESSAGES:]
    session.modified = True


def format_chat_history(history: list) -> str:
    """Format last 3 exchanges (6 messages) for the answer generation prompt."""
    if not history:
        return "No previous conversation."
    formatted = []
    for msg in history[-6:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        formatted.append(f"{role}: {msg['content']}")
    return "\n".join(formatted)


def format_rewrite_history(history: list) -> str:
    """
    Format ONLY the last 1 exchange (2 messages) for the query rewriter.
    The rewriter must resolve pronouns against the most recent topic only.
    Passing more history causes the LLM to pick up older topics by mistake.
    """
    if not history:
        return "No previous conversation."
    # Take only the last 2 messages (last user + last assistant)
    last_two = history[-2:]
    formatted = []
    for msg in last_two:
        role = "User" if msg["role"] == "user" else "Assistant"
        # Truncate long assistant answers — only the first 200 chars matter
        # for topic identification; full text confuses the rewriter
        content = msg["content"]
        if msg["role"] == "assistant" and len(content) > 200:
            content = content[:200].rsplit(" ", 1)[0] + "..."
        formatted.append(f"{role}: {content}")
    return "\n".join(formatted)


# ── Query rewriting ────────────────────────────────────────────────────────

def is_greeting_or_personal_question(user_query: str) -> bool:
    patterns = [
        r"\b(who are you|what are you|your name|introduce yourself)\b",
        r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b",
        r"\b(how are you|how do you do)\b",
    ]
    return any(re.search(p, user_query, re.IGNORECASE) for p in patterns)


def get_greeting_response(user_query: str) -> str | None:
    if re.search(r"\bwho are you|what are you|your name|introduce yourself\b", user_query, re.IGNORECASE):
        return ("I'm a Medical AI Assistant, designed to provide helpful medical information "
                "based on verified medical documents. I can answer questions about diseases, "
                "symptoms, causes, and general health topics. Please consult a doctor for "
                "personal medical advice.")
    if re.search(r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b", user_query, re.IGNORECASE):
        return "Hello! I'm your Medical AI Assistant. How can I help you with health-related questions today?"
    if re.search(r"\bhow are you\b", user_query, re.IGNORECASE):
        return "I'm functioning well, thank you! I'm ready to help answer your medical questions. What would you like to know?"
    return None


def _extract_rewritten_query(raw: str, original: str) -> str:
    """
    Strip chain-of-thought reasoning from the rewrite model output.
    The 8b model sometimes returns markdown reasoning before the actual query.

    Extraction order:
    1. Strip any inline label prefix on the same line  e.g. "Optimized Medical Search Query**: acne treatment"
    2. Look for a labelled block  e.g. "Optimized Query:\nacne treatment"
    3. Take the last short line (2-10 words, no sentence punctuation)
    4. Fall back to original
    """
    # Step 1: inline label on same line — "Label**: actual query" or "Label: actual query"
    inline = re.sub(
        r'^.*?(?:optimized(?:\s+medical)?\s+(?:search\s+)?query'
        r'|final\s+query|output)\s*\*{0,2}\s*[:\-]\s*',
        '', raw, flags=re.IGNORECASE
    ).strip().strip('*"\'')
    if inline and inline != raw.strip() and len(inline.split()) <= 12:
        return inline

    # Step 2: label on its own line, query on the next line
    block = re.search(
        r'(?:optimized(?:\s+medical)?\s+(?:search\s+)?query'
        r'|final\s+query|output)\s*\*{0,2}\s*[:\-]\s*\n+(.+)',
        raw, re.IGNORECASE
    )
    if block:
        candidate = block.group(1).strip().strip('*"\'')
        if candidate and len(candidate.split()) <= 12:
            return candidate

    # Step 3: last short non-reasoning line
    lines = [l.strip().strip('*"\'') for l in raw.splitlines() if l.strip()]
    for line in reversed(lines):
        if re.match(r'^[\d]+\.|^#{1,3}\s|^\*\*|^Based on|^This query|^Optimization', line):
            continue
        words = line.split()
        if 2 <= len(words) <= 10 and not line.endswith(('.', '!', '?')):
            return line

    return original


def rewrite_query_for_retrieval(user_query: str, chat_history_str: str = "") -> str:
    cleaned = user_query.strip()
    if not cleaned or is_greeting_or_personal_question(cleaned):
        return cleaned
    try:
        raw = get_query_rewrite_chain().invoke({
            "question":     cleaned,
            "chat_history": chat_history_str or "No previous conversation.",
        }).strip()
        rewritten = _extract_rewritten_query(raw, cleaned)
        if rewritten and rewritten != cleaned:
            logger.info(f"Query rewrite: '{cleaned}' -> '{rewritten}'")
        return rewritten
    except Exception as e:
        logger.warning(f"Query rewrite failed, using original: {e}")
    return cleaned


# ── Answer post-processing ─────────────────────────────────────────────────

def extract_subject_from_question(user_query: str) -> str:
    patterns = [
        r"^(?:what is|what's|whats|define|describe)\s+(.*)$",
        r"^(?:who is|what are)\s+(.*)$",
    ]
    normalized = user_query.strip().rstrip("?!. ")
    for pattern in patterns:
        m = re.match(pattern, normalized, flags=re.IGNORECASE)
        if m:
            subject = m.group(1).strip(" ?!.,:;")
            if subject:
                return subject
    return ""


_STRIP_RE = re.compile(
    r"^(?:based on the provided context|according to the provided context"
    r"|according to the context|this description(?: provided)?(?: matches the characteristics of)?"
    r"|this describes|this is describing|the description provided"
    r"|this condition|it is described as|this is|it is)\s*[:,.\-]*\s*",
    re.IGNORECASE,
)

# Emergency sentences — highest priority, shown first in safety block
_EMERGENCY_RE = re.compile(
    r"(?:SEEK\s+IMMEDIATE\s+EMERGENCY|call\s+911|call\s+your\s+local\s+emergency"
    r"|go\s+to\s+(?:the\s+)?(?:nearest\s+)?emergency|do\s+not\s+(?:wait|delay)"
    r"|this\s+(?:is\s+a\s+)?(?:medical\s+)?emergency"
    r"|national\s+suicide\s+prevention|crisis\s+(?:text\s+)?line)",
    re.IGNORECASE,
)

# Disclaimer/consult sentences — shown after content, before emergency if both present
_DISCLAIMER_RE = re.compile(
    r"(?:it(?:'s| is) (?:essential|important|crucial|critical|recommended|advisable)"
    r"|(?:please\s+)?(?:consult|see|visit|speak(?:\s+with)?|talk(?:\s+to)?)\s+"
    r"(?:a\s+)?(?:qualified\s+)?(?:doctor|physician|healthcare|medical|specialist|"
    r"provider|professional|oncologist|dermatologist|cardiologist|endocrinologist)"
    r"|(?:seek|get)\s+(?:immediate|urgent|professional|medical|emergency)\s+"
    r"(?:care|help|attention|advice|evaluation|treatment)"
    r"|your\s+healthcare\s+provider\s+(?:will|can|should|must)"
    r"|(?:a\s+)?(?:doctor|physician|healthcare\s+professional|specialist)\s+"
    r"(?:can|will|should|must|would)"
    r"|for\s+(?:a\s+)?(?:comprehensive|personalized|proper|accurate|correct|complete)\s+"
    r"(?:understanding|diagnosis|evaluation|assessment|treatment|recommendation|advice)"
    r"|(?:this\s+)?(?:information\s+)?(?:is\s+)?(?:not\s+a\s+substitute|does\s+not\s+replace)"
    r"\s+(?:for\s+)?(?:professional|medical)"
    r"|always\s+(?:consult|seek|verify|check\s+with)"
    r"|your\s+(?:specific\s+)?(?:situation|case|condition)\s+requires)"
    r"|(?:please\s+)?(?:consult|see)\s+(?:a\s+)?(?:doctor|physician|specialist|healthcare)",
    re.IGNORECASE,
)


def _sentence_split(text: str) -> list[str]:
    """Split a prose paragraph into individual sentences."""
    # Split on sentence-ending punctuation (including colon for "include: xxx" patterns)
    parts = re.split(r'(?<=[.!?:])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def restructure_response(answer_text: str) -> str:
    """
    Enforce strict response structure:
      1. Intro sentence (if present)
      2. Bullet list / main content
      3. [blank line]
      4. Disclaimer / consult note
      5. Emergency note (if present)

    Works by:
    - Splitting prose paragraphs into sentences
    - Classifying each sentence as: content | disclaimer | emergency
    - Reassembling in the correct order
    """
    if not answer_text:
        return answer_text

    lines = answer_text.replace("\r\n", "\n").split("\n")

    content_parts: list[str] = []
    disclaimer_parts: list[str] = []
    emergency_parts: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Preserve blank lines only within content (not after disclaimers start)
            if not disclaimer_parts and not emergency_parts:
                content_parts.append("")
            continue

        is_bullet = stripped.startswith(("- ", "• ", "* ", "· "))

        if is_bullet:
            # Bullets are always content — never move them
            content_parts.append(line)
        else:
            # Split prose lines into sentences and classify each
            sentences = _sentence_split(stripped)
            pending_content: list[str] = []

            disclaimer_mode = False  # Once true, all remaining sentences are disclaimer
            for sent in sentences:
                if _EMERGENCY_RE.search(sent):
                    emergency_parts.append(sent)
                elif disclaimer_mode or _DISCLAIMER_RE.search(sent):
                    # Once we hit a disclaimer, EVERYTHING after it is also disclaimer
                    # (LLM chains disclaimer sentences together)
                    if not disclaimer_mode and pending_content:
                        # First disclaimer - flush prior content
                        content_parts.append(" ".join(pending_content))
                        pending_content = []
                    disclaimer_mode = True
                    disclaimer_parts.append(sent)
                else:
                    pending_content.append(sent)

            if pending_content:
                # Re-join content sentences back into a paragraph line
                content_parts.append(" ".join(pending_content))

    # Clean trailing blank lines from content
    while content_parts and not content_parts[-1].strip():
        content_parts.pop()

    # Assemble final response
    sections: list[str] = []

    if content_parts:
        sections.append("\n".join(content_parts))

    if disclaimer_parts:
        # Deduplicate and join into one clean sentence
        seen = set()
        unique = []
        for d in disclaimer_parts:
            key = re.sub(r'\s+', ' ', d.lower().strip())
            if key not in seen:
                seen.add(key)
                unique.append(d)
        sections.append(" ".join(unique))

    if emergency_parts:
        # Emergency always last and clearly marked
        emergency_text = " ".join(emergency_parts)
        sections.append(f"⚠️ {emergency_text}")

    return "\n\n".join(sections)


def clean_answer_text(user_query: str, answer_text: str) -> str:
    if not answer_text:
        return answer_text

    trimmed  = answer_text.strip()
    stripped = _STRIP_RE.sub("", trimmed).strip()
    subject  = extract_subject_from_question(user_query)

    if subject and len(subject) <= 40 and len(subject.split()) <= 5:
        m = re.search(rf"\b{re.escape(subject)}\b", stripped, flags=re.IGNORECASE)
        if m:
            remainder = stripped[m.end():].lstrip(" ,:-.")
            if remainder:
                return f"{subject[:1].upper() + subject[1:]} is {remainder}"

    if stripped and stripped != trimmed:
        return stripped[:1].upper() + stripped[1:]

    return trimmed


def format_answer_for_readability(user_query: str, answer_text: str) -> str:
    if not answer_text:
        return answer_text

    formatted = answer_text.replace("\r\n", "\n").strip()
    is_list_q = bool(re.search(
        r"\b(cause|causes|symptom|symptoms|signs|reason|reasons|risk factors|types|steps|how)\b",
        user_query, re.IGNORECASE,
    ))

    # Normalise bullet markers to "- "
    formatted = re.sub(r"(?m)^\s*[•·\*]\s+", "- ", formatted)
    formatted = re.sub(r"\n{3,}", "\n\n", formatted)
    formatted = formatted.lstrip("\n")

    # If it's a list question but no bullets exist yet, convert sentences to bullets
    if is_list_q and "\n- " not in formatted:
        sentences = [p.strip() for p in re.split(r"(?<=[.!?])\s+", formatted) if p.strip()]
        if len(sentences) >= 2:
            formatted = sentences[0] + "\n" + "\n".join(f"- {s}" for s in sentences[1:6])

    return formatted


def needs_clinical_safety_note(user_query: str) -> bool:
    return bool(re.search(
        r"\b(pain|abdomen|abdominal|stomach|medicine|medication|tablet|dose"
        r"|treatment|treat|symptom|fever|vomit|nausea|diarrhea|bleeding|chest)\b",
        user_query, re.IGNORECASE,
    ))


def append_clinical_safety_note(user_query: str, answer_text: str) -> str:
    """
    Appends a safety note only if none already exists at the end.
    restructure_response() has already moved disclaimers/emergency to the end,
    so this only adds a note when the LLM omitted one entirely.
    """
    if not answer_text:
        return answer_text

    if not needs_clinical_safety_note(user_query):
        return answer_text

    # Check last 300 chars for existing consult/emergency note
    tail = answer_text[-300:]
    if re.search(
        r"\b(consult|doctor|physician|healthcare|emergency|urgent care|911)\b",
        tail, re.IGNORECASE,
    ):
        return answer_text

    # Append appropriate note
    if re.search(
        r"\b(severe|unbearable|worsening|persistent|blood|bleeding|faint|fainting|chest)\b",
        user_query, re.IGNORECASE,
    ):
        note = "⚠️ If symptoms are severe or worsening, seek emergency medical care immediately."
    else:
        note = "💡 Please consult a doctor or healthcare professional for proper diagnosis and personalised advice."

    return f"{answer_text}\n\n{note}"


# ── Flask routes ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template('chat.html')


@app.route("/clear", methods=["POST"])
def clear_chat():
    session['chat_history'] = []
    session.modified = True
    return "Conversation history cleared."


@app.route("/get", methods=["GET", "POST"])
def chat():
    user_query = request.form.get("msg", "").strip()
    if not user_query:
        return "Please enter a message."

    get_session_memory()
    history = session.get('chat_history', [])

    # Full history for answer generation (last 3 exchanges = 6 messages)
    chat_history_str = format_chat_history(history)
    # Only last 1 exchange for query rewriting — prevents picking up old topics
    rewrite_history_str = format_rewrite_history(history)

    greeting = get_greeting_response(user_query)
    if greeting:
        update_session_memory(user_query, greeting)
        return greeting

    retrieval_query = rewrite_query_for_retrieval(user_query, rewrite_history_str)
    logger.info(f"User: '{user_query}' | Rewritten: '{retrieval_query}'")

    try:
        final_answer = get_rag_chain().invoke({
            "input":           user_query,
            "retrieval_query": retrieval_query,
            "chat_history":    chat_history_str,
        })
        final_answer = clean_answer_text(user_query, str(final_answer))
        final_answer = format_answer_for_readability(user_query, final_answer)
        final_answer = restructure_response(final_answer)
        final_answer = append_clinical_safety_note(user_query, final_answer)


        update_session_memory(user_query, final_answer)
        logger.info("Response generated successfully.")
        return final_answer


    except Exception as error:
        import traceback
        logger.error(f"RAG pipeline failed: {error}")
        logger.error(traceback.format_exc())
        return "I'm sorry, I encountered a technical issue while processing your request. Please try again in a moment."


# ── Startup preload ────────────────────────────────────────────────────────


def preload_models():
    """Warm up all cached singletons at startup to avoid first-request latency."""
    logger.info("Preloading models...")
    steps = [
        ("Embeddings",          get_embeddings),
        ("LLM",                 get_llm),
        ("Extractor LLM",       get_extractor_llm),
        ("Hybrid chunks",       get_chunks),
        ("BM25 index",          get_bm25_retriever),
        ("Compressor pipeline", get_compressor_pipeline),
        ("Baseline retriever",  get_retriever),
        ("RAG chain",           get_rag_chain),
    ]
    for name, fn in steps:
        try:
            fn()
            logger.info(f"  ✓ {name} ready")
        except Exception as e:
            logger.warning(f"  ✗ {name} failed to preload: {e}")


if __name__ == '__main__':
    preload_models()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

