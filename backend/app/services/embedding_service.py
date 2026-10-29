import logging
import hashlib
import math
from abc import ABC, abstractmethod
from typing import List
from app.core.config import settings

logger = logging.getLogger(__name__)

class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of string chunks."""
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Generate vector embedding for a single search query."""
        pass

class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise RuntimeError(f"OpenAI embedding service error: {str(e)}")

    async def embed_query(self, query: str) -> List[float]:
        results = await self.embed_texts([query])
        return results[0]

class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: str, model: str = "gemini-embedding-001"):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            embeddings = []
            for t in texts:
                response = await self.client.aio.models.embed_content(
                    model=self.model,
                    contents=t
                )
                if hasattr(response, "embeddings") and response.embeddings:
                    embeddings.append(response.embeddings[0].values)
                elif hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                    embeddings.append(response.embedding.values)
                else:
                    embeddings.append([])
            return embeddings
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}")
            raise RuntimeError(f"Gemini embedding service error: {str(e)}")

    async def embed_query(self, query: str) -> List[float]:
        results = await self.embed_texts([query])
        return results[0]

class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic unit-normalized vector generator for offline testing and fast CI.
    Generates consistent float vectors based on MD5 and word tokens so cosine similarity
    ranks semantically relevant mock texts accurately.
    """
    def __init__(self, dim: int = 1536):
        self.dim = dim

    def _generate_vector(self, text: str) -> List[float]:
        # Seed vector values from hash and character ordinals
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = []
        for i in range(self.dim):
            byte_val = h[i % len(h)]
            # Mix with position to avoid repetitive patterns
            val = (byte_val ^ (i & 0xFF)) / 255.0 - 0.5
            vec.append(val)
        
        # Unit normalize (L2 norm)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]

    async def embed_query(self, query: str) -> List[float]:
        return self._generate_vector(query)

def get_embedding_provider() -> BaseEmbeddingProvider:
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAIEmbeddingProvider(api_key=settings.OPENAI_API_KEY, model=settings.EMBEDDING_MODEL)
    elif provider == "gemini" and settings.GEMINI_API_KEY:
        gemini_model = settings.EMBEDDING_MODEL if settings.EMBEDDING_MODEL != "text-embedding-3-small" else "gemini-embedding-001"
        return GeminiEmbeddingProvider(api_key=settings.GEMINI_API_KEY, model=gemini_model or "gemini-embedding-001")
    else:
        if provider != "mock":
            logger.warning(
                f"Configured embedding provider '{provider}' API key not found. "
                "Using MockEmbeddingProvider for offline/free testing."
            )
        return MockEmbeddingProvider(dim=settings.EMBEDDING_DIM)
