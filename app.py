import warnings
warnings.filterwarnings("ignore")
from functools import lru_cache
import re
import threading
import uuid
import copy
import time
from typing import List, Any, Optional, Dict, Mapping

from flask import Flask, render_template, request, session, jsonify

from src.helper import download_hugging_face_embeddings, chunk_pdf_dir
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_core.retrievers import BaseRetriever
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
from langchain_core.documents import Document as LCDocument
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun, CallbackManagerForRetrieverRun
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict
from typing import List, Any, Optional, Dict
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

# Temporary response cache to recover answers when the browser/proxy times out
# before the backend returns the final payload.
COMPLETED_RESPONSE_CACHE = {}

# Feature availability flags
ADVANCED_RETRIEVAL_AVAILABLE = True


# ─── Configuration ────────────────────────────────────────────────
# Set to True to use advanced retrieval with hybrid search & query expansion
USE_ADVANCED_RETRIEVAL = os.environ.get('USE_ADVANCED_RETRIEVAL', 'False').lower() == 'true'
USE_QUERY_EXPANSION = os.environ.get('USE_QUERY_EXPANSION', 'False').lower() == 'true'

if USE_ADVANCED_RETRIEVAL and not ADVANCED_RETRIEVAL_AVAILABLE:
    logger.warning("Advanced retrieval is enabled but module not available. Install with: pip install rank-bm25")
    USE_ADVANCED_RETRIEVAL = False

logger.info(f"Advanced retrieval: {'ENABLED' if USE_ADVANCED_RETRIEVAL else 'DISABLED'}")
logger.info(f"Query expansion: {'ENABLED' if USE_QUERY_EXPANSION else 'DISABLED'}")

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

load_dotenv()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
# Collect all possible Groq keys for rotation
_GROQ_KEYS = [
    os.environ.get('GROQ_API_KEY'),
    os.environ.get('GROQ_EVAL_API_KEY'),
    os.environ.get('growth_api_pickup') # mentioned in .env comment
]
GROQ_API_KEYS = [k for k in _GROQ_KEYS if k and k.strip()]
GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else None

if not PINECONE_API_KEY or not GROQ_API_KEYS:
    logger.error("Missing critical API keys (Pinecone or Groq) in environment variables!")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY or ""
if GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# ── Intent keywords for response formatting ──────────────────────────────────
_INTENT_KEYWORDS = {
    "symptoms": ["Symptoms", "Signs and Symptoms", "Clinical Manifestations"],
    "causes": ["Causes", "Etiology", "Risk Factors"],
    "treatment": ["Treatment", "Management", "Therapy", "Medications"],
    "diagnosis": ["Diagnosis", "Diagnostic Tests"],
}

# ── Thread-local Request Logging ───────────────────────────────────────────
class RequestLogs:
    """Helper to collect log entries for the current request context."""
    def __init__(self):
        self._storage = threading.local()
        if not hasattr(self._storage, 'entries'):
            self._storage.entries = []

    def log(self, level, message):
        if not hasattr(self._storage, 'entries'):
            self._storage.entries = []
        self._storage.entries.append({
            'timestamp': time.time(),
            'level': level,
            'message': message
        })

    def info(self, msg): self.log('INFO', msg)
    def warning(self, msg): self.log('WARNING', msg)
    def error(self, msg): self.log('ERROR', msg)

    @property
    def entries(self):
        return getattr(self._storage, 'entries', [])

    def get_all(self):
        """Regression support: return all entries."""
        return self.entries

    def clear(self):
        if hasattr(self._storage, 'entries'):
            self._storage.entries = []

request_logs = RequestLogs()

# ── Rotating LLM Class ─────────────────────────────────────────────────────

class RotatingGroqLLM:
    """
    A wrapper around ChatGroq that rotates through multiple API keys on 429 errors.
    Inherits from nothing to avoid Pydantic v1/v2 deepcopy conflicts.
    """
    def __init__(self, api_keys: List[str], model_name: str, temperature: float = 0.0):
        self.api_keys = api_keys
        self.model_name = model_name
        self.temperature = temperature
        self.current_idx = 0
        self._init_llm()

    def _init_llm(self):
        from langchain_groq import ChatGroq
        if not self.api_keys:
            raise ValueError("No API keys provided for RotatingGroqLLM")
        
        llm_instance = ChatGroq(
            model=self.model_name,
            temperature=self.temperature,
            groq_api_key=self.api_keys[self.current_idx]
        )
        self._llm = llm_instance

    def rotate(self):
        """Switch to the next API key."""
        if len(self.api_keys) > 1:
            self.current_idx = (self.current_idx + 1) % len(self.api_keys)
            logger.info(f"↺ Rate limit hit. Switched to Groq key {self.current_idx + 1}/{len(self.api_keys)}")
            self._init_llm()
            return True
        return False

    def invoke(self, *args, **kwargs):
        """Invoke the current LLM with retry logic for rate limits."""
        for _ in range(len(self.api_keys) + 1):
            try:
                return self._llm.invoke(*args, **kwargs)
            except Exception as e:
                err = str(e).lower()
                if "429" in err or "rate_limit" in err:
                    if not self.rotate():
                        raise e
                else:
                    raise e
        raise RuntimeError("Max retries exceeded with key rotation.")

    def stream(self, *args, **kwargs):
        """Stream from the current LLM with retry logic for rate limits."""
        for _ in range(len(self.api_keys) + 1):
            try:
                yield from self._llm.stream(*args, **kwargs)
                return
            except Exception as e:
                err = str(e).lower()
                if "429" in err or "rate_limit" in err:
                    if not self.rotate():
                        raise e
                else:
                    raise e
        raise RuntimeError("Max retries exceeded with key rotation.")

    def ainvoke(self, *args, **kwargs):
        """Async invoke with retry logic."""
        async def _run():
            for _ in range(len(self.api_keys) + 1):
                try:
                    return await self._llm.ainvoke(*args, **kwargs)
                except Exception as e:
                    err = str(e).lower()
                    if "429" in err or "rate_limit" in err:
                        if not self.rotate():
                            raise e
                    else:
                        raise e
            raise RuntimeError("Max retries exceeded with key rotation.")
        import asyncio
        return _run()

    async def astream(self, *args, **kwargs):
        """Async stream with retry logic."""
        for _ in range(len(self.api_keys) + 1):
            try:
                async for chunk in self._llm.astream(*args, **kwargs):
                    yield chunk
                return
            except Exception as e:
                err = str(e).lower()
                if "429" in err or "rate_limit" in err:
                    if not self.rotate():
                        raise e
                else:
                    raise e
        raise RuntimeError("Max retries exceeded with key rotation.")

    def __call__(self, *args, **kwargs):
        return self.invoke(*args, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "rotating-groq"

    # Minimal Runnable interface implementation
    def batch(self, inputs, config=None, **kwargs):
        return [self.invoke(x, config, **kwargs) for x in inputs]
    
    async def abatch(self, inputs, config=None, **kwargs):
        return [await self.ainvoke(x, config, **kwargs) for x in inputs]

_MAX_QUERY_LENGTH = 500
MAX_QUERY_LENGTH = _MAX_QUERY_LENGTH  # alias used in validate_user_input
_UNSAFE_QUERY_PATTERN = re.compile(
    r"(<\s*/?\s*script\b|javascript:|on\w+\s*=|<\s*img\b|<\s*iframe\b)",
    flags=re.IGNORECASE,
)
_EMERGENCY_QUERY_PATTERN = re.compile(
    r"\b(chest pain|difficulty breathing|shortness of breath|stroke|seizure|"
    r"unconscious|fainting|severe bleeding|overdose|poisoning|suicidal|heart attack)\b",
    flags=re.IGNORECASE,
)

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
    """Single LLM instance shared by the RAG chain with key rotation."""
    if len(GROQ_API_KEYS) > 1:
        return RotatingGroqLLM(api_keys=GROQ_API_KEYS, model_name="llama-3.3-70b-versatile", temperature=0.1)
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)


@lru_cache(maxsize=1)
def get_query_rewrite_chain():
    if len(GROQ_API_KEYS) > 1:
        rewrite_llm = RotatingGroqLLM(api_keys=GROQ_API_KEYS, model_name="llama-3.1-8b-instant", temperature=0)
    else:
        rewrite_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    
    rewrite_prompt = ChatPromptTemplate.from_messages([
        ("system", query_rewrite_system_prompt),
        ("human", "Chat history:\n{chat_history}\n\nUser query: {question}"),
    ])
    return rewrite_prompt | rewrite_llm | StrOutputParser()


# ── Metadata-aware retrieval ───────────────────────────────────────────────

_INTENT_SECTION_MAP: list[tuple[re.Pattern, list[str]]] = [
    (
        re.compile(r"\b(symptom|symptoms|sign|signs|present|presentation|feel|feeling|experience|look\s+like|looks\s+like)\b", re.IGNORECASE),
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
            class _FilteredBM25Retriever(BaseRetriever):
                """BM25 wrapper with Python-side section post-filtering."""
                model_config = ConfigDict(arbitrary_types_allowed=True)

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

def _clean_chunk(text: str) -> str:
    """
    Clean a retrieved PDF chunk before sending to the LLM.
    Removes timestamps, UI artifacts, broken newlines, and excessive whitespace.
    """
    # Remove timestamps like 22:44 or 9:05
    text = re.sub(r'\b\d{1,2}:\d{2}\b', '', text)
    # Remove common UI artifacts from PDF extraction
    text = re.sub(r'Type your question or message', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Ask a medical question\.?\.?\.?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Evidence-based health information', '', text, flags=re.IGNORECASE)
    # Remove page numbers like "Page 1" or standalone numbers
    text = re.sub(r'\bPage\s+\d+\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    # Collapse multiple newlines into one
    text = re.sub(r'\n{2,}', '\n', text)
    # Collapse multiple spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # Remove lines that are just punctuation or single characters
    text = re.sub(r'(?m)^\s*[^\w\s]{1,3}\s*$', '', text)
    return text.strip()


def _format_docs(docs) -> str:
    """Concatenate retrieved docs with section + page metadata headers. Cleans each chunk first."""
    parts = []
    for doc in docs:
        section = doc.metadata.get("section", "")
        page    = doc.metadata.get("page", "")
        header  = f"[Section: {section} | Page: {page}]" if section else ""
        cleaned = _clean_chunk(doc.page_content)
        if cleaned:
            parts.append(f"{header}\n{cleaned}".strip())
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


def has_ambiguous_pronoun(text: str) -> bool:
    return bool(re.search(r"\b(it|this|that|its|they|them|their|these|those)\b", text, re.IGNORECASE))


def validate_user_input(user_query: str) -> tuple[bool, str]:
    """Validate user input for emptiness, length, and unsafe content."""
    if user_query is None:
        return False, "Please enter a message."

    cleaned_query = user_query.strip()
    if not cleaned_query:
        return False, "Please enter a message."

    if len(cleaned_query) > MAX_QUERY_LENGTH:
        return False, f"Please keep your message under {MAX_QUERY_LENGTH} characters."

    if "<" in cleaned_query or ">" in cleaned_query or _UNSAFE_QUERY_PATTERN.search(cleaned_query):
        return False, "Please remove HTML or script-like content from your message."

    return True, cleaned_query


def detect_emergency_keywords(user_query: str) -> bool:
    """Detect symptom patterns that warrant urgent-care guidance."""
    if not user_query:
        return False
    return bool(_EMERGENCY_QUERY_PATTERN.search(user_query))


COMMON_QUERY_FIXES = [
    (r"\bwhats\b", "what is"),
    (r"\bwht\b", "what"),
    (r"\bwat\b", "what"),
    (r"\bthsi\b", "this"),
    (r"\bteh\b", "the"),
    (r"\bhv\b", "have"),
    (r"\bproblm\b", "problem"),
    (r"\brpoblem\b", "problem"),
    (r"\bprblm\b", "problem"),
    (r"\bseveree\b", "severe"),
    (r"\bsleepy\b", "sleep"),
    (r"\bslep\b", "sleep"),
    (r"\binsomina\b", "insomnia"),
    (r"\bsomnia\b", "insomnia"),
    (r"\bmeds\b", "medications"),
    (r"\bmeds?cine\b", "medicine"),
    (r"\bmedc?ation\b", "medication"),
    (r"\btreatmnt\b", "treatment"),
    (r"\btretment\b", "treatment"),
    (r"\bcaust\b", "cause"),
    (r"\bcauses?\b", "cause"),
    (r"\bdepresion\b", "depression"),
    (r"\banxity\b", "anxiety"),
    (r"\bdiabtes\b", "diabetes"),
    (r"\bdiabts\b", "diabetes"),
    (r"\bhypertention\b", "hypertension"),
    (r"\bhypertenssion\b", "hypertension"),
    (r"\bacnee\b", "acne"),
    (r"\bfeaver\b", "fever"),
    (r"\bferver\b", "fever"),
    (r"\bcaugh\b", "cough"),
    (r"\bbreth\b", "breath"),
    (r"\bpainn\b", "pain"),
    (r"\bvacci?nat?ion\b", "vaccination"),
]


def normalize_informal_query(text: str) -> str:
    """Normalize common shorthand/typos from chat-style input for better intent parsing."""
    if not text:
        return ""

    normalized = f" {text.lower().strip()} "

    # Normalize common chat shorthand and spelling mistakes before any topic matching.
    replacements = [
        (r"(?<=\s)n(?=\s)", " and "),
        (r"\bplz\b", "please"),
        (r"\bcuz\b", "cause"),
        (r"\bfr\b", "for"),
        (r"\bmed\b", "medication"),
        (r"\bmeds\b", "medications"),
    ]
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    for pattern, replacement in COMMON_QUERY_FIXES:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    # Collapse repeated spaces and trim the padding we added for boundary-safe matching.
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def extract_primary_topic(text: str) -> str:
    if not text:
        return ""

    normalized = text.strip().rstrip("?!. ")
    patterns = [
        r"^(?:what is|what's|whats|define|describe|tell me about|explain)\s+(.*)$",
        r"^(?:how to treat|how do i treat|how is .* treated|treatment for)\s+(.*)$",
        r"^(?:what causes|why does|why do)\s+(.*)$",
        r"^(?:symptoms of|signs of|what are the symptoms of)\s+(.*)$",
        r"^(?:prevention of|how to prevent|how can i prevent)\s+(.*)$",
    ]

    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            candidate = re.split(r"\b(and|or|with|in|for)\b", match.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
            topic = candidate.strip(" ,.:;?!")
            if topic:
                return topic.lower()

    # Fallback: capture simple noun phrase after common medical intent words.
    fallback = re.search(
        r"\b(?:about|for|of|regarding)\s+([a-zA-Z0-9\- ]{3,50})$",
        normalized,
        flags=re.IGNORECASE,
    )
    if fallback:
        return fallback.group(1).strip(" ,.:;?!").lower()

    return ""


def infer_topic_from_query(text: str) -> str:
    """Infer topic from informal user query (e.g., 'i hv severe problem in sleep wht medication to take')."""
    if not text:
        return ""

    query = normalize_informal_query(text)

    topic_keywords = {
        "sleep": "sleep problems",
        "insomnia": "sleep problems",
        "acne": "acne",
        "diabetes": "diabetes",
        "hypertension": "hypertension",
        "blood pressure": "hypertension",
        "asthma": "asthma",
        "bronchitis": "bronchitis",
        "eczema": "eczema",
    }
    for key, topic in topic_keywords.items():
        if key in query:
            return topic

    # Examples: problem in sleep, issues with stomach, etc.
    problem_match = re.search(r"\b(?:problem|problems|issue|issues)\s+(?:in|with)\s+([a-z0-9\- ]{2,40})", query)
    if problem_match:
        candidate = problem_match.group(1).strip(" ,.:;?!")
        if candidate:
            return candidate

    patterns = [
        r"\b(?:what is|what's|what are|tell me about|about|causes of|symptoms of|treatment for|management of|prevent)\s+([a-z0-9\- ]{2,50})",
        r"\b([a-z0-9\- ]{2,40})\s+(?:medication|medicine|treatment|therapy)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            candidate = match.group(1).strip(" ,.:;?!")
            if candidate:
                return candidate

    return extract_primary_topic(query)


def get_recent_topic(chat_history: list) -> str:
    if not chat_history:
        return ""

    # Strong preference: most recent user message to preserve user intent.
    for msg in reversed(chat_history[-8:]):
        if msg.get("role") == "user":
            topic = infer_topic_from_query(msg.get("content", ""))
            if topic:
                return topic

    # Fallback: assistant content only if user topic is unavailable.
    for msg in reversed(chat_history[-4:]):
        if msg.get("role") == "assistant":
            topic = infer_topic_from_query(msg.get("content", ""))
            if topic:
                return topic
    return ""


def build_topic_anchored_query(query: str, topic: str) -> str:
    q = query.strip().lower()
    if not topic:
        return query

    if re.search(r"\b(treat|treatment|manage|management|therapy)\b", q):
        return f"treatment for {topic}"
    if re.search(r"\b(symptom|symptoms|sign|signs)\b", q):
        return f"symptoms of {topic}"
    if re.search(r"\b(cause|causes|why)\b", q):
        return f"causes of {topic}"
    if re.search(r"\b(prevent|prevention)\b", q):
        return f"prevention of {topic}"
    if re.search(r"\b(complication|complications|risk|risks)\b", q):
        return f"complications of {topic}"

    # Generic fallback if intent is ambiguous.
    return f"{q} {topic}".strip()


def _build_rag_chain(llm, strict_structure: bool = False):
    from langchain_core.runnables import RunnableLambda, RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser

    def build_prompt(input_dict):
        chat_history = input_dict.get("chat_history", "No previous conversation.")
        context_docs = input_dict.get("context", [])
        topic_ref = input_dict.get("topic_reference", "").strip()

        # If an explicit topic reference is provided, prepend it to chat history
        if topic_ref:
            chat_history = f"Referenced topic (from conversation): {topic_ref}\n\n{chat_history}"

        if strict_structure:
            # Keep fallback prompt compact for 3.1 token budget.
            concise_chunks = []
            for doc in context_docs[:2]:
                text = re.sub(r"\s+", " ", doc.page_content).strip()
                if text:
                    concise_chunks.append(text[:520])
            context = "\n\n".join(concise_chunks)
        else:
            context = _format_docs(context_docs)

        # Use the original user question for the answer prompt, NOT the rewritten search query
        question = input_dict.get("input", "")

        # Format system prompt with all variables
        formatted_system = system_prompt.format(
            chat_history=chat_history,
            context=context if context else "[No relevant documents found]",
            input=question
        )

        if strict_structure:
            formatted_system += (
                "\n\nFALLBACK RESPONSE RULES (MANDATORY):\n"
                "1) Keep response under 8 lines total.\n"
                "2) Start with a direct 1-sentence answer to the user question.\n"
                "3) Then provide 3-5 bullet points only, no headings.\n"
                "4) Do not include phrases like 'additional resources', 'recommendation', or meta-instructions.\n"
                "5) Avoid repeating symptoms/points.\n"
                "6) Put one short disclaimer sentence only at the end.\n"
            )

        return ChatPromptTemplate.from_messages([
            ("system", formatted_system)
        ])

    def get_retriever_input(x):
        # Use the rewritten query for retrieval if available, otherwise the original input
        query = str(x.get("retrieval_query", x.get("input", "")))
        return query

    def per_query_retrieval(query):
        """Build a custom retriever with metadata filters based on the query."""
        retriever_obj = build_per_query_retriever(query)
        docs = retriever_obj.invoke(query)
        return docs

    def log_retrieval_results(docs):
        logger.info(f"Retrieved {len(docs)} documents after reranking.")
        for i, doc in enumerate(docs[:3]):  # Log top 3 for brevity
            source = doc.metadata.get('source', 'Unknown')
            section = doc.metadata.get('section', 'N/A')
            content_preview = doc.page_content[:100].replace('\n', ' ')
            logger.info(f"  -> Doc {i+1} | Section: {section} | Content: {content_preview}...")
        return docs

    chain = (
        RunnablePassthrough.assign(context=get_retriever_input | RunnableLambda(per_query_retrieval) | log_retrieval_results)
        | RunnableLambda(build_prompt)
        | llm
        | StrOutputParser()
    )

    return chain

# ── Query rewriting ────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_rag_chain():
    return _build_rag_chain(get_llm(), strict_structure=False)


@lru_cache(maxsize=1)
def get_rag_chain_fallback():
    return _build_rag_chain(get_llm(), strict_structure=True)


def is_rate_limit_error(error: Exception) -> bool:
    error_text = str(error).lower()
    error_type = error.__class__.__name__.lower()
    return (
        "ratelimit" in error_type
        or "rate limit" in error_text
        or "rate_limit_exceeded" in error_text
        or "error code: 429" in error_text
    )


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


def rewrite_query_for_retrieval(user_query: str, chat_history: list = None, current_topic: str = "") -> str:
    cleaned_query = user_query.strip()
    if not cleaned_query:
        return ""

    # Don't rewrite greetings/personal questions
    if is_greeting_or_personal_question(cleaned_query):
        return cleaned_query

    try:
        history = chat_history or []
        if isinstance(history, str):
            history = [{"role": "user", "content": history}]
        # Rewrite uses only the most recent turn context to avoid topic drift.
        current_history = format_rewrite_history(history)
        recent_topic = current_topic or get_recent_topic(history)
        normalized_query = normalize_informal_query(cleaned_query)
        query_for_rewrite = normalized_query

        # Deterministically anchor ambiguous pronouns to the most recent topic.
        if has_ambiguous_pronoun(normalized_query) and recent_topic:
            anchored = build_topic_anchored_query(cleaned_query, recent_topic)
            print(f"DEBUG: Pronoun anchored deterministically: '{cleaned_query}' -> '{anchored}'")
            return anchored

        print(f"DEBUG: Rewriting query. History length: {len(current_history)} chars.")

        rewritten_query = get_query_rewrite_chain().invoke({
            "question": query_for_rewrite,
            "chat_history": current_history
        }).strip()

        if has_ambiguous_pronoun(normalized_query) and recent_topic:
            # Guardrail: if the model still returns unresolved pronouns, force topic anchoring.
            if has_ambiguous_pronoun(rewritten_query):
                rewritten_query = build_topic_anchored_query(cleaned_query, recent_topic)

        if rewritten_query:
            print(f"DEBUG: Original: '{cleaned_query}' -> Optimized: '{rewritten_query}'")
            return rewritten_query
    except Exception as rewrite_error:
        print(f"Query rewrite failed, falling back to original query: {rewrite_error}")
    return cleaned_query


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


def _fix_when_to_seek_section(text: str) -> str:
    """
    Remove '## When to Seek Medical Attention' if it only contains a generic
    consult/disclaimer sentence (not real emergency warning signs).
    The disclaimer will be appended properly at the end instead.
    """
    lines = text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Detect the "When to Seek" header
        if re.match(r'^##\s+When to Seek', stripped, re.IGNORECASE):
            # Collect the content of this section (until next ## or end)
            section_lines = []
            j = i + 1
            while j < len(lines):
                next_stripped = lines[j].strip()
                if next_stripped.startswith("##") or next_stripped == "---":
                    break
                if next_stripped:
                    section_lines.append(next_stripped)
                j += 1

            # Check if section only has generic disclaimer text (no real warning signs)
            section_text = " ".join(section_lines)
            has_real_warnings = bool(re.search(
                r'\b(severe|sudden|emergency|911|immediately|urgent|worsening|'
                r'chest pain|stroke|bleeding|unconscious|seizure|high fever|'
                r'difficulty breathing|swelling|infection|abscess)\b',
                section_text, re.IGNORECASE
            ))

            if has_real_warnings:
                # Keep the section — it has real clinical content
                result.append(line)
            else:
                # Drop the header and its generic content — disclaimer goes at end
                i = j
                continue
        else:
            result.append(line)
        i += 1

    return "\n".join(result)


def restructure_response(answer_text: str) -> str:
    """
    Post-process LLM response:
    1. Remove '## When to Seek' if it only contains a generic disclaimer
    2. Extract any mid-content disclaimer sentences and move to end
    3. Ensure emergency notes are clearly marked
    """
    if not answer_text:
        return answer_text

    # Step 1: fix the "When to Seek" section
    text = _fix_when_to_seek_section(answer_text)

    lines = text.replace("\r\n", "\n").split("\n")
    content_parts: list[str] = []
    disclaimer_parts: list[str] = []
    emergency_parts: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not disclaimer_parts and not emergency_parts:
                content_parts.append("")
            continue

        # Section headers and bullets are always content
        is_bullet  = stripped.startswith(("- ", "• ", "* ", "· "))
        is_header  = stripped.startswith("##")
        is_divider = stripped == "---"

        if is_bullet or is_header or is_divider:
            content_parts.append(line)
        else:
            sentences = _sentence_split(stripped)
            pending: list[str] = []
            disclaimer_mode = False

            for sent in sentences:
                if _EMERGENCY_RE.search(sent):
                    emergency_parts.append(sent)
                elif disclaimer_mode or _DISCLAIMER_RE.search(sent):
                    if not disclaimer_mode and pending:
                        content_parts.append(" ".join(pending))
                        pending = []
                    disclaimer_mode = True
                    disclaimer_parts.append(sent)
                else:
                    pending.append(sent)

            if pending:
                content_parts.append(" ".join(pending))

    # Clean trailing blank lines
    while content_parts and not content_parts[-1].strip():
        content_parts.pop()

    sections: list[str] = []
    if content_parts:
        sections.append("\n".join(content_parts))

    if disclaimer_parts:
        seen: set[str] = set()
        unique: list[str] = []
        for d in disclaimer_parts:
            key = re.sub(r'\s+', ' ', d.lower().strip())
            if key not in seen:
                seen.add(key)
                unique.append(d)
        # Format as italic disclaimer after ---
        disclaimer_text = " ".join(unique)
        if not disclaimer_text.startswith("*"):
            disclaimer_text = f"*{disclaimer_text}*"
        sections.append(f"---\n{disclaimer_text}")

    if emergency_parts:
        sections.append(f"⚠️ {' '.join(emergency_parts)}")

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


def dedupe_repeated_lines(answer_text: str) -> str:
    if not answer_text:
        return answer_text

    lines = [line.strip() for line in answer_text.replace("\r\n", "\n").split("\n")]
    seen = set()
    cleaned_lines = []
    for line in lines:
        if not line:
            continue
        key = re.sub(r"\s+", " ", line).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def strip_meta_instruction_leakage(answer_text: str) -> str:
    if not answer_text:
        return answer_text
    blocked_phrases = (
        "disclaimer placement",
        "this response includes a disclaimer",
        "as per the guidelines",
        "based on the provided context",
        "according to the provided context",
        "direct answer",
        "direct answer:",
    )
    lines = [line.strip() for line in answer_text.replace("\r\n", "\n").split("\n")]
    kept = []
    for line in lines:
        if not line:
            continue
        lower_line = line.lower()
        if any(phrase in lower_line for phrase in blocked_phrases):
            continue
        kept.append(line)
    cleaned = "\n".join(kept).strip()
    # Remove common banner tokens like "Direct Answer:" which models sometimes inject
    cleaned = re.sub(r"\bDirect Answer:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Direct Answer\b[:\-\s]*", "", cleaned, flags=re.IGNORECASE | re.M)
    cleaned = re.sub(r"\b(Additional Resources|Recommendation):\s*(?=\.|$)", "", cleaned, flags=re.IGNORECASE)
    # Remove explicit 'Direct Answer:' tokens if present
    cleaned = re.sub(r"\bDirect Answer:\b", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def looks_unstructured_or_noisy(answer_text: str) -> bool:
    if not answer_text:
        return False
    lower_text = answer_text.lower()
    indicators = [
        "disclaimer placement",
        "this response includes a disclaimer",
        "additional resources:",
        "recommendation:",
    ]
    noisy_markers = sum(1 for marker in indicators if marker in lower_text)
    sentence_count = len([s for s in re.split(r"(?<=[.!?])\s+", answer_text) if s.strip()])
    return noisy_markers > 0 or sentence_count > 14


def enforce_compact_structure(user_query: str, answer_text: str) -> str:
    if not answer_text:
        return answer_text
    def sanitize_sentence_fragment(text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        # Drop orphan list markers such as "1." that appear after splitting.
        if re.fullmatch(r"\d+[\.)]?", cleaned):
            return ""
        # Repair dangling list lead-ins like "consider the following steps: 1."
        cleaned = re.sub(r"(\b(?:steps?|points?|tips?)\s*:)\s*\d+[\.)]?\s*$", r"\1", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    query_tokens = {
        token
        for token in re.findall(r"[a-z]{4,}", user_query.lower())
        if token not in {"what", "which", "with", "have", "from", "that", "your", "about", "girl", "years", "year", "suffering"}
    }
    sentences = []
    for part in re.split(r"(?<=[.!?])\s+", answer_text.replace("\n", " ").strip()):
        cleaned_part = sanitize_sentence_fragment(part)
        if cleaned_part:
            sentences.append(cleaned_part)
    if not sentences:
        return answer_text

    scored = []
    for sentence in sentences:
        sentence_tokens = set(re.findall(r"[a-z]{4,}", sentence.lower()))
        overlap = len(query_tokens.intersection(sentence_tokens))
        scored.append((overlap, sentence))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_sentences = [s for score, s in scored if score > 0][:6]

    if not top_sentences:
        top_sentences = sentences[:4]

    intro = "Here is a focused answer:"
    if top_sentences:
        intro = top_sentences[0]

    bullets = top_sentences[1:5]
    if not bullets:
        return intro

    bullet_text = "\n".join(f"- {item}" for item in bullets)
    return f"{intro}\n{bullet_text}".strip()


def is_medication_query(user_query: str) -> bool:
    return bool(
        re.search(
            r"\b(pill|pills|tablet|tablets|medicine|medicines|medication|drug|drugs|what to take|which medicine)\b",
            user_query,
            flags=re.IGNORECASE,
        )
    )


def stabilize_medication_answer(user_query: str, answer_text: str) -> str:
    if not is_medication_query(user_query):
        return answer_text

    # Only apply diabetes-specific template if diabetes is actually mentioned in the answer
    if not re.search(r"\b(diabetes|blood sugar|glucose|hba1c|insulin|metformin|sugar level)\b", answer_text.lower()):
        return answer_text

    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", answer_text.replace("\n", " ").strip())
        if s.strip()
    ]

    med_keywords = re.compile(
        r"\b(metformin|insulin|sulfonylurea|sulfonylureas|sglt2|dpp-4|glp-1|thiazolidinedione|medication|medicine|drug)\b",
        flags=re.IGNORECASE,
    )

    medication_points = []
    seen = set()
    for sentence in sentences:
        if not med_keywords.search(sentence):
            continue
        normalized = re.sub(r"\s+", " ", sentence).strip(" -•")
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        medication_points.append(normalized)
        if len(medication_points) == 4:
            break

    if not medication_points:
        medication_points = [
            "Metformin is often first-line for type 2 diabetes, based on doctor evaluation.",
            "Insulin is required for type 1 diabetes and in some type 2 cases.",
            "Other tablet options depend on sugar levels, kidney function, weight, and side-effect risk.",
        ]

    bullet_text = "\n".join(f"- {point}" for point in medication_points)

    return (
        "I cannot safely tell you exactly which pill to start online. "
        "The right medicine depends on your diabetes type, blood sugar reports, and medical history.\n\n"
        "Common doctor-selected options include:\n"
        f"{bullet_text}\n\n"
        "Next steps:\n"
        "- Book a diabetes consultation for a personalized prescription.\n"
        "- Share your recent blood glucose and HbA1c reports.\n"
        "- If you have vomiting, severe weakness, confusion, or very high sugars, seek urgent care."
    )


def needs_clinical_safety_note(user_query: str) -> bool:
    return bool(re.search(
        r"\b(pain|headache|abdomen|abdominal|stomach|medicine|medication|tablet|dose"
        r"|treatment|treat|symptom|fever|vomit|nausea|diarrhea|bleeding|chest|illness|drug)\b",
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

def move_disclaimer_to_end(answer_text: str) -> str:
    if not answer_text:
        return answer_text

    disclaimer_pattern = re.compile(
        r"\b(consult|doctor|physician|healthcare provider|healthcare professional|not a substitute|cannot diagnose|personalized medical advice|qualified professional|urgent medical care|emergency services)\b",
        flags=re.IGNORECASE,
    )

    # Split by newline and sentence punctuation boundaries.
    raw_parts = re.split(r"\n+|(?<=[.!?])\s+", answer_text.strip())
    content_parts = []
    disclaimer_parts = []

    for part in raw_parts:
        chunk = part.strip()
        if not chunk:
            continue
        if disclaimer_pattern.search(chunk):
            disclaimer_parts.append(chunk)
        else:
            content_parts.append(chunk)

    # Deduplicate disclaimers while preserving order.
    seen = set()
    deduped = []
    for item in disclaimer_parts:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    body = "\n".join(content_parts).strip()
    if not deduped:
        return body if body else answer_text.strip()

    disclaimer_block = " ".join(deduped).strip()
    if body:
        return f"{body}\n\n{disclaimer_block}"
    return disclaimer_block


@app.route("/")
def index():
    get_session_memory()
    return render_template('chat.html')


@app.route("/health", methods=["GET"])
def health():
    """Basic health endpoint for load balancers and container probes."""
    return jsonify({"status": "ok"}), 200


@app.route("/clear", methods=["POST"])
def clear_chat():
    session['chat_history'] = []
    session.modified = True
    return "Conversation history cleared."


@app.route("/response-status", methods=["POST"])
def response_status():
    request_id = request.form.get("request_id", "").strip()
    if not request_id:
        return jsonify({"status": "invalid"}), 400

    answer = COMPLETED_RESPONSE_CACHE.pop(request_id, None)
    if answer is None:
        return jsonify({"status": "pending"}), 200

    return jsonify({"status": "ready", "answer": answer}), 200


@app.route("/get", methods=["GET", "POST"])
def chat():
    raw_query = request.form.get("msg", "")
    request_id = request.form.get("request_id", "").strip()
    is_valid, validation_result = validate_user_input(raw_query)
    if not is_valid:
        return validation_result

    user_query = validation_result

    if 'chat_history' not in session:
        session['chat_history'] = []
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
        if request_id:
            COMPLETED_RESPONSE_CACHE[request_id] = final_answer
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

