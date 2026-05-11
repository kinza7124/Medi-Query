"""
Improved Retrieval Pipeline
============================
Implements hybrid search combining BM25 (lexical) and semantic search,
query expansion, and multi-query generation for better retrieval.
"""

import logging
from typing import List, Dict, Tuple
from abc import ABC, abstractmethod

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain_pinecone import PineconeVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
import numpy as np

logger = logging.getLogger(__name__)


class QueryExpander:
    """Generate expanded and alternative query formulations"""
    
    def __init__(self, llm: ChatGroq = None):
        """Initialize with an LLM for query generation"""
        self.llm = llm or ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.3
        )
    
    def expand_query(self, query: str) -> List[str]:
        """
        Generate multiple query formulations
        
        Args:
            query: Original user query
            
        Returns:
            List of expanded queries
        """
        expansion_prompt = ChatPromptTemplate.from_template(
            """You are a medical search expert. Generate 3 alternative formulations 
            of the following medical question to capture different aspects and terminology.
            Return ONLY the 3 queries, one per line, without numbering.
            
            Original question: {query}
            
            Alternative formulations:"""
        )
        
        chain = expansion_prompt | self.llm | StrOutputParser()
        
        try:
            response = chain.invoke({"query": query})
            # Parse response into individual queries
            expanded_queries = [
                q.strip() 
                for q in response.split('\n') 
                if q.strip()
            ]
            
            # Add original query
            all_queries = [query] + expanded_queries[:3]
            logger.info(f"Generated {len(all_queries)} query formulations")
            return all_queries
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return [query]


class HybridRetriever:
    """Combines BM25 (lexical) and semantic search"""
    
    def __init__(
        self,
        documents: List[Document],
        embeddings: HuggingFaceEmbeddings,
        index_name: str = "medical-chatbot"
    ):
        """
        Initialize hybrid retriever
        
        Args:
            documents: List of documents for BM25 indexing
            embeddings: Embeddings model for semantic search
            index_name: Pinecone index name
        """
        # BM25 Retriever
        self.bm25_retriever = BM25Retriever.from_documents(
            documents,
            k=10
        )
        
        # Semantic Retriever (Pinecone)
        self.semantic_retriever = PineconeVectorStore.from_existing_index(
            index_name=index_name,
            embedding=embeddings,
        ).as_retriever(
            search_type="mmr",
            search_kwargs={"k": 10, "fetch_k": 30, "lambda_mult": 0.5}
        )
    
    def retrieve(self, query: str, k: int = 10) -> List[Document]:
        """
        Hybrid retrieval combining BM25 and semantic search
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of retrieved documents
        """
        try:
            # Get results from both retrievers
            bm25_docs = self.bm25_retriever.invoke(query)
            semantic_docs = self.semantic_retriever.invoke(query)
            
            # Combine and deduplicate
            combined = {}
            
            # Add BM25 results (weight: 0.4)
            for i, doc in enumerate(bm25_docs):
                score = (1.0 / (i + 1)) * 0.4  # Reciprocal rank weighting
                doc_id = doc.page_content[:100]  # Use content hash as ID
                combined[doc_id] = {
                    'doc': doc,
                    'score': score
                }
            
            # Add semantic results (weight: 0.6)
            for i, doc in enumerate(semantic_docs):
                score = (1.0 / (i + 1)) * 0.6
                doc_id = doc.page_content[:100]
                if doc_id in combined:
                    combined[doc_id]['score'] += score
                else:
                    combined[doc_id] = {
                        'doc': doc,
                        'score': score
                    }
            
            # Sort by score and return top k
            sorted_results = sorted(
                combined.items(),
                key=lambda x: x[1]['score'],
                reverse=True
            )
            
            results = [item[1]['doc'] for item in sorted_results[:k]]
            logger.info(f"Hybrid retrieval returned {len(results)} documents")
            return results
            
        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {e}")
            return []


class RerankingStrategy(ABC):
    """Base class for reranking strategies"""
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_n: int = 5
    ) -> List[Document]:
        """Rerank documents for a given query"""
        pass


class CrossEncoderReranker(RerankingStrategy):
    """Rerank using cross-encoder models"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize with cross-encoder model"""
        self.model = HuggingFaceCrossEncoder(model_name=model_name)
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_n: int = 5
    ) -> List[Document]:
        """Rerank documents using cross-encoder"""
        try:
            texts = [doc.page_content for doc in documents]
            scores = self.model.predict([[query, text] for text in texts])
            
            # Sort by scores
            ranked_indices = np.argsort(scores)[::-1][:top_n]
            reranked_docs = [documents[i] for i in ranked_indices]
            
            logger.info(f"Reranked to top {len(reranked_docs)} documents")
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}")
            return documents[:top_n]


class DiversityReranker(RerankingStrategy):
    """Rerank to maximize diversity"""
    
    def __init__(self, embeddings: HuggingFaceEmbeddings):
        """Initialize with embeddings model"""
        self.embeddings = embeddings
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_n: int = 5
    ) -> List[Document]:
        """Rerank to maximize diversity"""
        try:
            if not documents:
                return documents
            
            # Compute embeddings
            embeddings_list = [
                self.embeddings.embed_query(doc.page_content)
                for doc in documents
            ]
            
            # Greedy selection for diversity
            selected_indices = [0]  # Start with first document
            selected_embeddings = [embeddings_list[0]]
            
            while len(selected_indices) < min(top_n, len(documents)):
                best_idx = -1
                best_score = -1
                
                for idx, emb in enumerate(embeddings_list):
                    if idx in selected_indices:
                        continue
                    
                    # Compute minimum distance to selected documents
                    distances = [
                        np.linalg.norm(np.array(emb) - np.array(sel_emb))
                        for sel_emb in selected_embeddings
                    ]
                    min_distance = min(distances)
                    
                    if min_distance > best_score:
                        best_score = min_distance
                        best_idx = idx
                
                if best_idx != -1:
                    selected_indices.append(best_idx)
                    selected_embeddings.append(embeddings_list[best_idx])
            
            reranked_docs = [documents[i] for i in selected_indices]
            logger.info(f"Diversity reranked to {len(reranked_docs)} documents")
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Diversity reranking failed: {e}")
            return documents[:top_n]


class AdvancedRetriever:
    """Complete advanced retrieval pipeline"""
    
    def __init__(
        self,
        documents: List[Document] = None,
        embeddings: HuggingFaceEmbeddings = None,
        llm: ChatGroq = None,
        index_name: str = "medical-chatbot"
    ):
        """Initialize advanced retriever"""
        self.embeddings = embeddings
        self.llm = llm or ChatGroq(model="llama-3.1-8b-instant")
        
        # Initialize components
        self.query_expander = QueryExpander(self.llm)
        
        if documents:
            self.hybrid_retriever = HybridRetriever(
                documents, embeddings, index_name
            )
        else:
            self.hybrid_retriever = None
        
        self.cross_encoder_reranker = CrossEncoderReranker()
        self.diversity_reranker = DiversityReranker(embeddings)
    
    def retrieve_with_expansion(
        self,
        query: str,
        use_expansion: bool = True,
        use_hybrid: bool = True,
        use_reranking: bool = True,
        top_n: int = 5
    ) -> List[Document]:
        """
        Advanced retrieval with query expansion and reranking
        
        Args:
            query: Original user query
            use_expansion: Generate alternative queries
            use_hybrid: Use hybrid (BM25 + semantic) search
            use_reranking: Rerank results
            top_n: Number of final results
            
        Returns:
            List of top documents
        """
        all_docs = {}
        
        # Query expansion
        queries = [query]
        if use_expansion:
            queries = self.query_expander.expand_query(query)
        
        # Retrieve for each query
        for q in queries:
            try:
                if use_hybrid and self.hybrid_retriever:
                    docs = self.hybrid_retriever.retrieve(q, k=15)
                else:
                    docs = []  # Fallback
                
                # Deduplicate
                for doc in docs:
                    doc_id = doc.page_content[:100]
                    if doc_id not in all_docs:
                        all_docs[doc_id] = doc
                        
            except Exception as e:
                logger.error(f"Retrieval failed for query '{q}': {e}")
                continue
        
        # Convert to list
        docs_list = list(all_docs.values())
        
        if not docs_list:
            logger.warning("No documents retrieved")
            return []
        
        # Reranking
        if use_reranking:
            docs_list = self.cross_encoder_reranker.rerank(
                query, docs_list, top_n
            )
            # Optional: apply diversity reranking
            docs_list = self.diversity_reranker.rerank(
                query, docs_list, top_n
            )
        
        logger.info(f"Advanced retrieval retrieved {len(docs_list)} documents")
        return docs_list[:top_n]


def create_improved_rag_chain(
    retriever: AdvancedRetriever,
    llm: ChatGroq = None
) -> any:
    """
    Create an improved RAG chain with better retrieval
    
    Args:
        retriever: Advanced retriever instance
        llm: Language model for generation
        
    Returns:
        RAG chain
    """
    if llm is None:
        llm = ChatGroq(model="llama-3.3-70b-versatile")
    
    # System prompt for generation
    system_prompt = """You are a Senior Medical AI Consultant. 
    Answer questions using ONLY the provided medical context.
    If the context is insufficient, state clearly that information is not available.
    Be concise, professional, and accurate."""
    
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Context:\n{context}\n\nQuestion: {input}""")
    ])
    
    # Create stuff documents chain
    combine_docs_chain = create_stuff_documents_chain(llm, qa_prompt)
    
    # Create retrieval chain
    chain = create_retrieval_chain(
        retriever.hybrid_retriever.semantic_retriever if hasattr(retriever, 'hybrid_retriever') else None,
        combine_docs_chain
    )
    
    return chain


if __name__ == "__main__":
    logger.info("Improved Retrieval Module loaded")
    logger.info("Use AdvancedRetriever for enhanced RAG pipelines")
