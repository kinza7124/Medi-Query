# Medical AI Chatbot 🩺

A production-ready, RAG-enhanced (Retrieval-Augmented Generation) medical assistant designed to provide accurate, context-aware information from clinical datasets.

## 🌟 Key Features
- **Intelligent Retrieval**: Hybrid search combining BM25 (lexical) and MMR (semantic) dense retrieval.
- **Multi-turn Conversation**: Context-aware chat history management with pronoun resolution.
- **Clinical Safety**: Integrated safety triggers and disclaimers for sensitive medical queries.
- **RAGAS Evaluated**: High-performance metrics for answer relevancy and faithfulness.
- **High Performance**: Optimized with LLM rotation and connection pooling to handle rate limits.

## 🛠️ Tech Stack
- **Backend**: Flask (Python)
- **Orchestration**: LangChain
- **LLM**: Groq (Llama 3.3 70B)
- **Vector Database**: Pinecone
- **Embeddings**: BGE-Small-EN-V1.5 (HuggingFace)
- **Testing**: Pytest with environmental isolation mocking

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- Groq API Key
- Pinecone API Key

### 2. Installation
```bash
git clone https://github.com/kinza7124/medical-chatbot-ai.git
cd medical-chatbot-ai
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file in the root:
```env
PINECONE_API_KEY=your_pinecone_key
GROQ_API_KEY=your_groq_key
FLASK_SECRET_KEY=your_secret
```

### 4. Running the Application
```bash
python app.py
```
The app will be available at `http://127.0.0.1:5000`.

## 🧪 Testing
The project includes a robust test suite of 150+ cases.
```bash
pytest tests/ -v
```

## 📂 Project Structure
- `app.py`: Main Flask application and RAG pipeline.
- `src/`: Core logic for embeddings and data processing.
- `tests/`: Comprehensive unit, functional, and integration tests.
- `docs/`: Detailed SRS, Project Summary, and Testing documentation.

## ⚖️ Disclaimer
*This chatbot is for informational purposes only and is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician.*
