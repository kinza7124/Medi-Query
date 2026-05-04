from functools import lru_cache
import re
import uuid

from flask import Flask, render_template, request, session, jsonify
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from src.prompt import *
import logging
import os

# Optional: Import improved retrieval (available if installed)
try:
    from improved_retrieval import AdvancedRetriever, QueryExpander
    ADVANCED_RETRIEVAL_AVAILABLE = True
except ImportError:
    ADVANCED_RETRIEVAL_AVAILABLE = False

# Configure production-ready logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Temporary response cache to recover answers when the browser/proxy times out
# before the backend returns the final payload.
COMPLETED_RESPONSE_CACHE = {}

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

PINECONE_API_KEY=os.environ.get('PINECONE_API_KEY')
GROQ_API_KEY=os.environ.get('GROQ_API_KEY')

if not PINECONE_API_KEY or not GROQ_API_KEY:
    logger.error("Missing critical API keys in environment variables!")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY


@lru_cache(maxsize=1)
def get_embeddings():
    return download_hugging_face_embeddings()


@lru_cache(maxsize=1)
def get_docsearch():
    index_name = "medical-chatbot"
    return PineconeVectorStore.from_existing_index(
        index_name=index_name,
        embedding=get_embeddings(),
    )


@lru_cache(maxsize=1)
def get_retriever():
    docsearch = get_docsearch()
    base_retriever = docsearch.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 10, "fetch_k": 30, "lambda_mult": 0.5},
    )

    reranker_model = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    compressor = CrossEncoderReranker(model=reranker_model, top_n=4)
    return ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever,
    )


@lru_cache(maxsize=1)
def get_advanced_retriever():
    """Get advanced retriever with hybrid search and reranking"""
    if not ADVANCED_RETRIEVAL_AVAILABLE:
        logger.warning("Advanced retriever not available, falling back to standard retriever")
        return None

    try:
        embeddings = get_embeddings()
        llm = ChatGroq(model="llama-3.3-70b-versatile")

        advanced_retriever = AdvancedRetriever(
            embeddings=embeddings,
            llm=llm,
            index_name="medical-chatbot"
        )
        logger.info("Advanced retriever initialized")
        return advanced_retriever
    except Exception as e:
        logger.error(f"Failed to initialize advanced retriever: {e}")
        return None


def retrieve_with_enhancements(query: str, use_advanced: bool = None) -> list:
    """
    Retrieve documents with optional enhancements

    Args:
        query: Search query
        use_advanced: Use advanced retrieval (defaults to USE_ADVANCED_RETRIEVAL config)

    Returns:
        List of retrieved documents
    """
    use_advanced = use_advanced or USE_ADVANCED_RETRIEVAL

    if use_advanced:
        try:
            advanced_retriever = get_advanced_retriever()
            if advanced_retriever:
                docs = advanced_retriever.retrieve_with_expansion(
                    query=query,
                    use_expansion=USE_QUERY_EXPANSION,
                    use_hybrid=True,
                    use_reranking=True,
                    top_n=5
                )
                logger.info(f"Advanced retrieval: Retrieved {len(docs)} documents")
                return docs
        except Exception as e:
            logger.error(f"Advanced retrieval failed, fallback to standard: {e}")

    # Standard retrieval fallback
    retriever = get_retriever()
    docs = retriever.invoke(query)
    logger.info(f"Standard retrieval: Retrieved {len(docs)} documents")
    return docs


@lru_cache(maxsize=1)
def get_chat_model():
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


@lru_cache(maxsize=1)
def get_fallback_chat_model():
    # Keep fallback responses compact to reduce drift and improve structure quality.
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0, max_tokens=420)


@lru_cache(maxsize=1)
def get_query_rewrite_chain():
    query_rewrite_model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    query_rewrite_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", query_rewrite_system_prompt),
            ("human", "Chat history:\n{chat_history}\n\nUser query: {question}"),
        ]
    )
    return query_rewrite_prompt | query_rewrite_model | StrOutputParser()


def get_session_memory():
    """Get or create conversation memory for the current session."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session['chat_history'] = []
    return session['chat_history']


def update_session_memory(user_query: str, assistant_answer: str):
    """Update the session's chat history with a new exchange."""
    if 'chat_history' not in session:
        session['chat_history'] = []
    session['chat_history'].append({"role": "user", "content": user_query})
    session['chat_history'].append({"role": "assistant", "content": assistant_answer})
    # Limit chat history stored in the session cookie to avoid oversize cookie problems.
    # Keep only the most recent N messages (user+assistant entries count separately).
    MAX_SESSION_MESSAGES = 12
    try:
        session['chat_history'] = session['chat_history'][-MAX_SESSION_MESSAGES:]
    except Exception:
        # If anything goes wrong, fall back to a safe empty history.
        session['chat_history'] = []
    session.modified = True


def format_chat_history(history: list, max_messages: int = 10) -> str:
    """Format chat history list into a string for the prompt."""
    if not history:
        return "No previous conversation."
    formatted = []
    for msg in history[-max_messages:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        formatted.append(f"{role}: {msg['content']}")
    return "\n".join(formatted)


def format_docs(docs: list) -> str:
    """Format retrieved documents into a context string."""
    return "\n\n".join(doc.page_content for doc in docs)

def has_ambiguous_pronoun(text: str) -> bool:
    return bool(re.search(r"\b(it|this|that|its|they|them|their|these|those)\b", text, re.IGNORECASE))


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
            context = format_docs(context_docs)

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

    # Build the chain
    retriever = get_retriever()

    def get_retriever_input(x):
        # Use the rewritten query for retrieval if available, otherwise the original input
        query = str(x.get("retrieval_query", x.get("input", "")))
        print(f"DEBUG: [RETR-INPUT] Query for search: '{query}'")
        return query

    def log_retrieval_results(docs):
        print(f"DEBUG: [RETR-OUTPUT] Retrieved {len(docs)} documents after reranking.")
        for i, doc in enumerate(docs[:3]):  # Log top 3 for brevity
            source = doc.metadata.get('source', 'Unknown')
            content_preview = doc.page_content[:100].replace('\n', ' ')
            print(f"  -> Doc {i+1} | Source: {source} | Content: {content_preview}...")
        return docs

    chain = (
        RunnablePassthrough.assign(context=get_retriever_input | retriever | log_retrieval_results)
        | RunnableLambda(build_prompt)
        | llm
        | StrOutputParser()
    )

    return chain


@lru_cache(maxsize=1)
def get_rag_chain():
    return _build_rag_chain(get_chat_model(), strict_structure=False)


@lru_cache(maxsize=1)
def get_rag_chain_fallback():
    return _build_rag_chain(get_fallback_chat_model(), strict_structure=True)


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
    """Check if user is asking about the bot itself or greeting."""
    patterns = [
        r"\b(who are you|what are you|your name|introduce yourself)\b",
        r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b",
        r"\b(how are you|how do you do)\b",
    ]
    for pattern in patterns:
        if re.search(pattern, user_query, re.IGNORECASE):
            return True
    return False


def get_greeting_response(user_query: str) -> str:
    """Return appropriate greeting/personal response."""
    if re.search(r"\bwho are you|what are you|your name|introduce yourself\b", user_query, re.IGNORECASE):
        return "I'm a Medical AI Assistant, designed to provide helpful medical information based on verified medical documents. I can answer questions about diseases, symptoms, causes, and general health topics. Please consult a doctor for personal medical advice."
    elif re.search(r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b", user_query, re.IGNORECASE):
        return "Hello! I'm your Medical AI Assistant. How can I help you with health-related questions today?"
    elif re.search(r"\bhow are you\b", user_query, re.IGNORECASE):
        return "I'm functioning well, thank you! I'm ready to help answer your medical questions. What would you like to know?"
    return None


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
        current_history = format_chat_history(history, max_messages=2)
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


@lru_cache(maxsize=1)
def get_query_expander():
    """Get query expander for advanced retrieval"""
    if not ADVANCED_RETRIEVAL_AVAILABLE:
        return None

    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
        return QueryExpander(llm)
    except Exception as e:
        logger.warning(f"Failed to initialize query expander: {e}")
        return None


def expand_query_for_coverage(user_query: str) -> list:
    """
    Generate multiple query formulations for better retrieval coverage

    Args:
        user_query: Original user query

    Returns:
        List of expanded queries (including original)
    """
    if not USE_QUERY_EXPANSION:
        return [user_query]

    try:
        expander = get_query_expander()
        if expander:
            expanded = expander.expand_query(user_query)
            logger.info(f"Query expansion: Generated {len(expanded)} query formulations")
            return expanded
    except Exception as e:
        logger.warning(f"Query expansion failed: {e}")

    return [user_query]


def extract_subject_from_question(user_query: str) -> str:
    patterns = [
        r"^(?:what is|what's|whats|define|describe)\s+(.*)$",
        r"^(?:who is|what are)\s+(.*)$",
    ]

    normalized_query = user_query.strip().rstrip("?!. ")
    for pattern in patterns:
        match = re.match(pattern, normalized_query, flags=re.IGNORECASE)
        if match:
            subject = match.group(1).strip(" ?!.,:;")
            if subject:
                return subject

    return ""


def clean_answer_text(user_query: str, answer_text: str) -> str:
    if not answer_text:
        return answer_text

    trimmed_answer = answer_text.strip()
    lower_answer = trimmed_answer.lower()
    subject = extract_subject_from_question(user_query)
    bad_starts = (
        "based on the provided context",
        "according to the provided context",
        "according to the context",
        "this description",
        "this describes",
        "this is describing",
        "the description provided",
        "this condition",
        "it is described as",
        "this is",
        "it is",
    )

    def strip_leading_frame(text: str) -> str:
        return re.sub(
            r"^(?:based on the provided context|according to the provided context|according to the context|this description(?: provided)?(?: matches the characteristics of)?|this describes|this is describing|the description provided|this condition|it is described as|this is|it is)\s*[:,.-]*\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

    stripped_answer = strip_leading_frame(trimmed_answer)

    if subject:
        subject_match = re.search(rf"\b{re.escape(subject)}\b", stripped_answer, flags=re.IGNORECASE)
        if subject_match:
            remainder = stripped_answer[subject_match.end():].lstrip(" ,:-.")
            if remainder:
                cleaned = f"{subject[:1].upper() + subject[1:]} is {remainder}"
                return cleaned

    if lower_answer.startswith(bad_starts):
        fallback = strip_leading_frame(trimmed_answer)
        if fallback:
            if subject:
                subject_lower = subject.lower()
                if subject_lower in fallback.lower():
                    subject_index = fallback.lower().find(subject_lower)
                    remainder = fallback[subject_index + len(subject):].lstrip(" ,:-.")
                    if remainder:
                        return f"{subject[:1].upper() + subject[1:]} is {remainder}"
            return fallback[:1].upper() + fallback[1:]

    return trimmed_answer


def format_answer_for_readability(user_query: str, answer_text: str) -> str:
    if not answer_text:
        return answer_text

    formatted = answer_text.replace("\r\n", "\n").strip()
    lower_query = user_query.lower()
    is_list_question = bool(
        re.search(r"\b(cause|causes|symptom|symptoms|signs|reason|reasons|risk factors|types|steps|how)\b", lower_query)
    )

    # Normalize common list markers into consistent bullet lines.
    formatted = re.sub(r"(?m)^\s*[\*\u2022]\s+", "- ", formatted)
    formatted = re.sub(r"(?m)^\s*\d+[\.)]\s+", "- ", formatted)
    formatted = re.sub(r"(^|\s)\*\s+", r"\n- ", formatted)
    formatted = re.sub(r"\s+-\s+(?=[A-Za-z])", "\n- ", formatted)
    formatted = re.sub(r"(?m)^\s*\d+\.\s*$", "", formatted)
    formatted = re.sub(r"\n{3,}", "\n\n", formatted)
    formatted = formatted.lstrip("\n")

    if is_list_question and "\n- " not in formatted:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", formatted) if part.strip()]
        if len(sentences) >= 2:
            intro = sentences[0]
            bullet_lines = "\n".join(f"- {sentence}" for sentence in sentences[1:6])
            formatted = f"{intro}\n{bullet_lines}"

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
    return bool(
        re.search(
            r"\b(pain|abdomen|abdominal|stomach|medicine|medication|tablet|dose|treatment|treat|symptom|fever|vomit|nausea|diarrhea|bleeding)\b",
            user_query,
            flags=re.IGNORECASE,
        )
    )


def append_clinical_safety_note(user_query: str, answer_text: str) -> str:
    if not needs_clinical_safety_note(user_query):
        return answer_text

    # Remove any existing safety/consultation text from the answer
    safety_patterns = [
        r"\s*Consult a doctor or healthcare professional for proper evaluation and treatment[^.]*\.\s*",
        r"\s*Please consult a doctor or healthcare professional[^.]*\.\s*",
        r"\s*Please seek urgent medical care[^.]*\.\s*",
    ]
    cleaned_text = answer_text
    for pattern in safety_patterns:
        cleaned_text = re.sub(pattern, " ", cleaned_text, flags=re.IGNORECASE)
    cleaned_text = cleaned_text.strip()

    # Check if safety note already present after cleaning
    if re.search(r"\b(consult|doctor|physician|healthcare professional|emergency|urgent care)\b", cleaned_text, flags=re.IGNORECASE):
        return cleaned_text

    warning = "Please consult a doctor or healthcare professional for proper diagnosis and medicine advice."

    if re.search(r"\b(severe|unbearable|worsening|persistent|blood|bleeding|faint|fainting)\b", user_query, flags=re.IGNORECASE):
        warning = "Please seek urgent medical care immediately, and contact emergency services if symptoms are severe or worsening."

    return f"{cleaned_text}\n\n{warning}"


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
    return render_template('chat.html')


@app.route("/health", methods=["GET"])
def health():
    """Basic health endpoint for load balancers and container probes."""
    return jsonify({"status": "ok"}), 200


@app.route("/clear", methods=["POST"])
def clear_chat():
    """Clear the conversation history for the current session."""
    if 'chat_history' in session:
        session['chat_history'] = []
    if 'current_topic' in session:
        session['current_topic'] = ''
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
    user_query = request.form.get("msg", "").strip()
    request_id = request.form.get("request_id", "").strip()
    if not user_query:
        return "Please enter a message."

    # Initialize session memory
    get_session_memory()
    chat_history = session.get('chat_history', [])
    current_topic = session.get('current_topic', '')
    chat_history_str = format_chat_history(chat_history)

    # Check for greeting/personal questions first
    greeting_response = get_greeting_response(user_query)
    if greeting_response:
        update_session_memory(user_query, greeting_response)
        if request_id:
            COMPLETED_RESPONSE_CACHE[request_id] = greeting_response
        return greeting_response

    retrieval_query = rewrite_query_for_retrieval(user_query, chat_history, current_topic=current_topic)

    detected_topic = infer_topic_from_query(user_query)
    if detected_topic:
        session['current_topic'] = detected_topic
        session.modified = True
    elif has_ambiguous_pronoun(user_query) and current_topic:
        # Keep known topic for pronoun-only follow-ups.
        session['current_topic'] = current_topic
        session.modified = True

    logger.info(f"User query: '{user_query}' | Rewritten: '{retrieval_query}'")
    logger.debug(f"Session current_topic (before call): {session.get('current_topic','')}" )
    logger.debug(f"Detected topic: {detected_topic}")
    logger.debug(f"Retrieval query: {retrieval_query}")
    try:
        logger.debug(f"Chat history (truncated): {chat_history[-6:]}" )
    except Exception:
        logger.debug("Chat history unavailable or not list-like")

    try:
        request_payload = {
            "input": user_query,                 # Original question → shown to the LLM
            "retrieval_query": retrieval_query,  # Optimized query → used for vector search
            "chat_history": chat_history_str,
            "topic_reference": session.get('current_topic', '')
        }

        fallback_payload = {
            "input": user_query,
            "retrieval_query": retrieval_query,
            # Use shorter history for 3.1 fallback to avoid oversized prompts.
            "chat_history": format_chat_history(chat_history, max_messages=2),
            "topic_reference": session.get('current_topic', '')
        }

        # Pass BOTH the original user question (for the answer prompt)
        # and the rewritten query (for retrieval/search only)
        try:
            final_answer = get_rag_chain().invoke(request_payload)
        except Exception as primary_error:
            if is_rate_limit_error(primary_error):
                logger.warning("Primary model rate-limited. Retrying with fallback model.")
                final_answer = get_rag_chain_fallback().invoke(fallback_payload)
            else:
                raise

        final_answer = clean_answer_text(user_query, str(final_answer))
        final_answer = format_answer_for_readability(user_query, final_answer)
        final_answer = dedupe_repeated_lines(final_answer)
        final_answer = strip_meta_instruction_leakage(final_answer)
        if looks_unstructured_or_noisy(final_answer):
            final_answer = enforce_compact_structure(user_query, final_answer)
        final_answer = stabilize_medication_answer(user_query, final_answer)
        final_answer = append_clinical_safety_note(user_query, final_answer)
        final_answer = move_disclaimer_to_end(final_answer)
        # If the user used a pronoun (e.g., "it", "that") ensure the response
        # explicitly references the previous topic so it's clear what "it" refers to.
        try:
            if has_ambiguous_pronoun(user_query):
                recent_topic = current_topic or get_recent_topic(chat_history)
                if recent_topic:
                    # If the response doesn't already mention the recent topic, prepend a short reference.
                    if not re.search(r"\b" + re.escape(recent_topic) + r"\b", final_answer, flags=re.IGNORECASE):
                        final_answer = f"Referring to your earlier question about {recent_topic}:\n\n" + final_answer
        except Exception:
            # Keep going even if reference enrichment fails
            pass

        # Save to memory
        update_session_memory(user_query, final_answer)

        if request_id:
            COMPLETED_RESPONSE_CACHE[request_id] = final_answer

        logger.info("Successfully generated response.")
        return final_answer
    except Exception as error:
        import traceback
        logger.error(f"RAG pipeline failed: {error}")
        logger.error(traceback.format_exc())
        return "I'm sorry, I encountered a technical issue while processing your request. Please try again in a moment."


def preload_models():
    """Preload models at startup to prevent timeout on first request."""
    logger.info("Preloading models...")
    try:
        get_embeddings()
        print("✓ Embeddings loaded")
        get_chat_model()
        print("✓ Chat model loaded")
        get_retriever()
        print("✓ Retriever loaded")
        print("✓ All models preloaded successfully!")
    except Exception as e:
        print(f"Warning: Model preloading failed: {e}")


if __name__ == '__main__':
    preload_models()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
