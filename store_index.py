from dotenv import load_dotenv
import os
from src.helper import (
    chunk_pdf_dir,
    download_hugging_face_embeddings,
)
from pinecone import Pinecone
from pinecone import ServerlessSpec
from langchain_pinecone import PineconeVectorStore

load_dotenv()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

# ── 1. Parse PDFs once + hybrid chunk ──────────────────────────
# chunk_pdf_dir() opens each PDF with PyMuPDF exactly once, extracts
# layout blocks, detects sections, and runs token-aware semantic chunking.
# No double IO — replaces the old load_pdf_file → hybrid_chunk_documents chain.
print("Loading and chunking PDF documents (single parse)...")
text_chunks = chunk_pdf_dir('data/')
print(f"  Created {len(text_chunks)} hybrid chunks")

# Show a sample chunk + token distribution stats
if text_chunks:
    sample = text_chunks[0]
    print(f"\n  Sample chunk (#0):")
    print(f"    Section:      {sample.metadata.get('section', 'N/A')}")
    print(f"    Page:         {sample.metadata.get('page', 'N/A')}")
    print(f"    Content type: {sample.metadata.get('content_type', 'N/A')}")
    print(f"    Token count:  {sample.metadata.get('token_count', 'N/A')}")
    print(f"    Chunk type:   {sample.metadata.get('chunk_type', 'N/A')}")
    print(f"    Source:       {sample.metadata.get('source', 'N/A')}")
    preview = sample.page_content[:200].replace('\n', ' ')
    print(f"    Text:         {preview}...")

    # Token distribution across all chunks
    token_counts = [c.metadata.get("token_count", 0) for c in text_chunks]
    avg_tokens   = sum(token_counts) / len(token_counts)
    max_tokens   = max(token_counts)
    min_tokens   = min(token_counts)
    print(f"\n  Token stats across all chunks:")
    print(f"    avg={avg_tokens:.1f}  min={min_tokens}  max={max_tokens}")

# ── 2. Embeddings ───────────────────────────────────────────────
print("\nLoading embeddings model...")
embeddings = download_hugging_face_embeddings()

# ── 3. Pinecone setup ──────────────────────────────────────────
pinecone_api_key = PINECONE_API_KEY
pc = Pinecone(api_key=pinecone_api_key)

index_name = "medical-chatbot"

# Delete and recreate index to ensure clean re-indexing
existing_indexes = [idx.name for idx in pc.list_indexes()]
if index_name in existing_indexes:
    print(f"\nDeleting existing index '{index_name}' for clean re-index...")
    pc.delete_index(index_name)

print(f"Creating index '{index_name}'...")
pc.create_index(
    name=index_name,
    dimension=384,
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)

# Wait for index to be ready
import time
print("Waiting for index to be ready...")
while not pc.describe_index(index_name).status['ready']:
    time.sleep(1)
print("  Index is ready!")

# ── 4. Upload chunks ───────────────────────────────────────────
print(f"\nUploading {len(text_chunks)} chunks to Pinecone...")
docsearch = PineconeVectorStore.from_documents(
    documents=text_chunks,
    index_name=index_name,
    embedding=embeddings, 
)

print(f"\n✓ Successfully indexed {len(text_chunks)} hybrid chunks!")
print("  You can now restart the app with: python app.py")