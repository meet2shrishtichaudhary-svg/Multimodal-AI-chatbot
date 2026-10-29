import logging
import math
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.db.models import KnowledgeDocument, DocumentChunk
from app.services.embedding_service import get_embedding_provider
from app.utils.text_chunker import chunk_text
from app.schemas.rag import RAGChunkMatch
from app.schemas.chat import SourceCitation

logger = logging.getLogger(__name__)

async def index_document_content(
    db: Session,
    document: KnowledgeDocument,
    extracted_text: str,
    sections: List[Dict[str, Any]]
) -> int:
    """
    Chunks extracted document text, computes vector embeddings,
    and inserts chunks into the database.
    Returns total number of chunks created.
    """
    chunks_data = chunk_text(
        text=extracted_text,
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP
    )

    if not chunks_data:
        return 0

    chunk_texts = [c["chunk_text"] for c in chunks_data]
    embedding_provider = get_embedding_provider()
    embeddings = await embedding_provider.embed_texts(chunk_texts)

    for idx, c in enumerate(chunks_data):
        chunk_emb = embeddings[idx] if idx < len(embeddings) else None
        db_chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=c["chunk_index"],
            chunk_text=c["chunk_text"],
            embedding=chunk_emb,
            chunk_metadata=c.get("metadata", {})
        )
        db.add(db_chunk)

    document.total_chunks = len(chunks_data)
    db.commit()
    db.refresh(document)
    return len(chunks_data)

import re
import time
import math
import logging
import collections
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.db.models import KnowledgeDocument, DocumentChunk
from app.services.embedding_service import get_embedding_provider
from app.utils.text_chunker import chunk_text
from app.schemas.rag import RAGChunkMatch
from app.schemas.chat import SourceCitation

logger = logging.getLogger(__name__)

# In-memory retrieval cache: {cache_key: (timestamp, [RAGChunkMatch])}
_rag_retrieval_cache: Dict[str, Tuple[float, List[RAGChunkMatch]]] = {}
RAG_CACHE_TTL_SECONDS = 300.0

def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric words."""
    return [w.lower() for w in re.findall(r'\b\w+\b', text) if len(w) > 1]

def _compute_bm25_score(query_tokens: List[str], chunk_tokens: List[str], avg_doc_len: float, k1: float = 1.5, b: float = 0.75) -> float:
    """Compute BM25 score for a chunk against query tokens."""
    if not query_tokens or not chunk_tokens:
        return 0.0
    doc_len = len(chunk_tokens)
    counts = collections.Counter(chunk_tokens)
    score = 0.0
    for q in query_tokens:
        if q in counts:
            freq = counts[q]
            tf = (freq * (k1 + 1.0)) / (freq + k1 * (1.0 - b + b * (doc_len / max(avg_doc_len, 1.0))))
            score += tf
    return score

def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def clear_rag_cache_for_session(session_id: str):
    """Purges cached query results when documents in a session are updated or deleted."""
    global _rag_retrieval_cache
    keys_to_remove = [k for k in _rag_retrieval_cache if k.startswith(f"{session_id}:")]
    for k in keys_to_remove:
        _rag_retrieval_cache.pop(k, None)

async def retrieve_relevant_chunks(
    db: Session,
    session_id: str,
    query: str,
    top_k: int = None
) -> List[RAGChunkMatch]:
    """
    Hybrid Retrieval Engine:
    Combines dense semantic vector search (via pgvector or in-memory fallback)
    with sparse lexical BM25 token matching for high recall on both concepts and exact terms.
    Results are cached per session and query for optimal response latency.
    """
    if not query or not query.strip():
        return []

    # Check cache
    cache_key = f"{session_id}:{query.strip().lower()}"
    now = time.time()
    if cache_key in _rag_retrieval_cache:
        timestamp, cached_matches = _rag_retrieval_cache[cache_key]
        if now - timestamp < RAG_CACHE_TTL_SECONDS:
            return cached_matches

    # Check if session has uploaded documents
    has_docs = (
        db.query(KnowledgeDocument.id)
        .filter(KnowledgeDocument.session_id == session_id)
        .first()
    )
    if not has_docs:
        return []

    if top_k is None:
        top_k = settings.RAG_TOP_K

    try:
        embedding_provider = get_embedding_provider()
        query_vector = await embedding_provider.embed_query(query)
    except Exception as e:
        logger.warning(f"Embedding generation failed for RAG query ({e}). Skipping document grounding.")
        return []

    # Retrieve all chunks for the session
    chunks_query = (
        db.query(DocumentChunk, KnowledgeDocument.title)
        .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
        .filter(KnowledgeDocument.session_id == session_id)
        .all()
    )

    if not chunks_query:
        return []

    query_tokens = _tokenize(query)
    chunk_token_list = [_tokenize(chunk.chunk_text) for chunk, _ in chunks_query]
    total_tokens = sum(len(tokens) for tokens in chunk_token_list)
    avg_doc_len = total_tokens / max(len(chunk_token_list), 1)

    raw_candidates = []
    max_bm25 = 0.0

    for idx, (chunk, doc_title) in enumerate(chunks_query):
        # 1. Semantic Vector Similarity
        sem_sim = 0.0
        if chunk.embedding is not None:
            emb = chunk.embedding
            if isinstance(emb, str):
                import json
                try:
                    emb = json.loads(emb)
                except Exception:
                    emb = []
            if emb:
                sem_sim = _cosine_similarity(query_vector, emb)

        # 2. BM25 Lexical Score
        bm25_score = _compute_bm25_score(query_tokens, chunk_token_list[idx], avg_doc_len)
        if bm25_score > max_bm25:
            max_bm25 = bm25_score

        raw_candidates.append({
            "chunk": chunk,
            "doc_title": doc_title,
            "vector_sim": sem_sim,
            "bm25_score": bm25_score
        })

    # 3. Hybrid fusion: 65% dense semantic + 35% sparse lexical
    scored_matches = []
    for item in raw_candidates:
        normalized_bm25 = (item["bm25_score"] / max_bm25) if max_bm25 > 0 else 0.0
        # If query has exact term matches, boost score
        hybrid_score = (0.65 * item["vector_sim"]) + (0.35 * normalized_bm25)

        if hybrid_score >= settings.RAG_SIMILARITY_THRESHOLD or item["vector_sim"] >= settings.RAG_SIMILARITY_THRESHOLD:
            scored_matches.append((hybrid_score, item["chunk"], item["doc_title"]))

    scored_matches.sort(key=lambda x: x[0], reverse=True)
    top_matches = scored_matches[:top_k]

    result = [
        RAGChunkMatch(
            chunk_id=str(chunk.id),
            document_id=str(chunk.document_id),
            document_title=doc_title,
            chunk_index=chunk.chunk_index,
            text=chunk.chunk_text,
            similarity=float(score),
            metadata=chunk.chunk_metadata or {}
        )
        for score, chunk, doc_title in top_matches
    ]

    # Save to cache
    _rag_retrieval_cache[cache_key] = (now, result)
    return result

def build_rag_context_and_citations(
    chunks: List[RAGChunkMatch]
) -> Tuple[str, List[SourceCitation]]:
    """
    Formats chunks into LLM prompt context block and builds citations for UI.
    """
    if not chunks:
        return "", []

    context_lines = ["--- BEGIN RETRIEVED DOCUMENT CONTEXT ---"]
    citations = []

    for i, c in enumerate(chunks):
        tag = f"[Doc {i+1}: {c.document_title}]"
        context_lines.append(f"{tag}\n{c.text}\n")
        citations.append(SourceCitation(
            title=f"{c.document_title} (Part {c.chunk_index + 1})",
            url=None,
            snippet=c.text[:220] + "..." if len(c.text) > 220 else c.text,
            source_type="document",
            document_title=c.document_title
        ))

    context_lines.append(
        "--- END RETRIEVED DOCUMENT CONTEXT ---\n"
        "Instructions for Document Grounding:\n"
        "1. Base your answers strictly on the retrieved context above.\n"
        "2. If the context does not contain enough information to answer the question, clearly state: "
        "'The uploaded documents do not contain enough information to answer this question.'\n"
        "3. Cite the document names when providing facts."
    )

    return "\n".join(context_lines), citations
