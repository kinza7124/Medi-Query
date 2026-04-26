from functools import lru_cache
import re
import uuid

from flask import Flask, render_template, request, session
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
        search_kwargs={"k": 10, "fetch_k": 30, "lambda_mult": 0.7},
    )

    reranker_model = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    compressor = CrossEncoderReranker(model=reranker_model, top_n=4)
    return ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever,
    )


@lru_cache(maxsize=1)
def get_chat_model():
    return ChatGroq(model="llama-3.3-70b-versatile")


@lru_cache(maxsize=1)
def get_query_rewrite_chain():
    query_rewrite_model = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
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
    session.modified = True


def format_chat_history(history: list) -> str:
    """Format chat history list into a string for the prompt."""
    if not history:
        return "No previous conversation."
    formatted = []
    for msg in history[-10:]:  # Keep last 10 exchanges (20 messages)
        role = "User" if msg["role"] == "user" else "Assistant"
        formatted.append(f"{role}: {msg['content']}")
    return "\n".join(formatted)


@lru_cache(maxsize=1)
def get_rag_chain():
    from langchain_core.runnables import RunnableLambda, RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    
    # Create a simple chain that formats the prompt properly
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
    
    def build_prompt(input_dict):
        chat_history = input_dict.get("chat_history", "No previous conversation.")
        context = format_docs(input_dict.get("context", []))
        # Use the original user question for the answer prompt, NOT the rewritten search query
        question = input_dict.get("input", "")
        
        # Format system prompt with all variables
        formatted_system = system_prompt.format(
            chat_history=chat_history,
            context=context if context else "[No relevant documents found]",
            input=question
        )
        
        return ChatPromptTemplate.from_messages([
            ("system", formatted_system)
        ])
    
    # Build the chain
    retriever = get_retriever()
    llm = get_chat_model()
    
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


def rewrite_query_for_retrieval(user_query: str, chat_history_str: str = "") -> str:
    cleaned_query = user_query.strip()
    if not cleaned_query:
        return ""
    
    # Don't rewrite greetings/personal questions
    if is_greeting_or_personal_question(cleaned_query):
        return cleaned_query

    try:
        current_history = chat_history_str if chat_history_str else "No previous conversation."
        print(f"DEBUG: Rewriting query. History length: {len(current_history)} chars.")
        rewritten_query = get_query_rewrite_chain().invoke({
            "question": cleaned_query,
            "chat_history": current_history
        }).strip()
        if rewritten_query:
            print(f"DEBUG: Original: '{cleaned_query}' -> Optimized: '{rewritten_query}'")
            return rewritten_query
    except Exception as rewrite_error:
        print(f"Query rewrite failed, falling back to original query: {rewrite_error}")

    return cleaned_query


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
    formatted = re.sub(r"(^|\s)\*\s+", r"\n- ", formatted)
    formatted = re.sub(r"\s+-\s+(?=[A-Za-z])", "\n- ", formatted)
    formatted = re.sub(r"\n{3,}", "\n\n", formatted)
    formatted = formatted.lstrip("\n")

    if is_list_question and "\n- " not in formatted:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", formatted) if part.strip()]
        if len(sentences) >= 2:
            intro = sentences[0]
            bullet_lines = "\n".join(f"- {sentence}" for sentence in sentences[1:6])
            formatted = f"{intro}\n{bullet_lines}"

    return formatted


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


@app.route("/")
def index():
    return render_template('chat.html')


@app.route("/clear", methods=["POST"])
def clear_chat():
    """Clear the conversation history for the current session."""
    if 'chat_history' in session:
        session['chat_history'] = []
        session.modified = True
    return "Conversation history cleared."


@app.route("/get", methods=["GET", "POST"])
def chat():
    user_query = request.form.get("msg", "").strip()
    if not user_query:
        return "Please enter a message."

    # Initialize session memory
    get_session_memory()
    chat_history = session.get('chat_history', [])
    chat_history_str = format_chat_history(chat_history)

    # Check for greeting/personal questions first
    greeting_response = get_greeting_response(user_query)
    if greeting_response:
        update_session_memory(user_query, greeting_response)
        return greeting_response

    retrieval_query = rewrite_query_for_retrieval(user_query, chat_history_str)
    logger.info(f"User query: '{user_query}' | Rewritten: '{retrieval_query}'")
 
    try:
        # Pass BOTH the original user question (for the answer prompt)
        # and the rewritten query (for retrieval/search only)
        final_answer = get_rag_chain().invoke({
            "input": user_query,              # Original question → shown to the LLM
            "retrieval_query": retrieval_query,  # Optimized query → used for vector search
            "chat_history": chat_history_str
        })
        final_answer = clean_answer_text(user_query, str(final_answer))
        final_answer = format_answer_for_readability(user_query, final_answer)
        final_answer = append_clinical_safety_note(user_query, final_answer)
 
        # Save to memory
        update_session_memory(user_query, final_answer)
 
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