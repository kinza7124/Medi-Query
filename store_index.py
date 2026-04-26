from dotenv import load_dotenv
import os
from src.helper import (
    load_pdf_file,
    filter_to_minimal_docs,
    context_aware_split,
    download_hugging_face_embeddings,
)
from pinecone import Pinecone
from pinecone import ServerlessSpec 
from langchain_pinecone import PineconeVectorStore

load_dotenv()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

# ── 1. Load and clean documents ─────────────────────────────────
print("Loading PDF documents...")
extracted_data = load_pdf_file(data='data/')
print(f"  Loaded {len(extracted_data)} pages")

filter_data = filter_to_minimal_docs(extracted_data)

# ── 2. Context-aware chunking ───────────────────────────────────
print("Running context-aware chunking...")
text_chunks = context_aware_split(
    filter_data,
    chunk_size=800,
    chunk_overlap=100,
)
print(f"  Created {len(text_chunks)} contextualised chunks")

# Show a sample chunk
if text_chunks:
    sample = text_chunks[0]
    print(f"\n  Sample chunk (#{0}):")
    print(f"    Section: {sample.metadata.get('section', 'N/A')}")
    print(f"    Source:  {sample.metadata.get('source', 'N/A')}")
    preview = sample.page_content[:200].replace('\n', ' ')
    print(f"    Text:    {preview}...")

# ── 3. Embeddings ───────────────────────────────────────────────
print("\nLoading embeddings model...")
embeddings = download_hugging_face_embeddings()

# ── 4. Pinecone setup ──────────────────────────────────────────
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

# ── 5. Upload chunks ───────────────────────────────────────────
print(f"\nUploading {len(text_chunks)} chunks to Pinecone...")
docsearch = PineconeVectorStore.from_documents(
    documents=text_chunks,
    index_name=index_name,
    embedding=embeddings, 
)

print(f"\n✓ Successfully indexed {len(text_chunks)} context-aware chunks!")
print("  You can now restart the app with: python app.py")