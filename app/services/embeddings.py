from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.rate_limiters import InMemoryRateLimiter
from app.core.config import settings

class EmbeddingService:
    _base_embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        api_key=settings.GEMINI_AI_API_KEY,
        max_retries=0, # disable retry to avoid exhausting free tier API resources
    )

    @classmethod
    async def generate_embeddings(cls, texts: list[str], is_query: bool = False):
        """
        Handles both single queries (returns flat list) and 
        multiple documents (returns list of lists).
        """
        if is_query:
            # 1. Use aembed_query for questions
            # Result: [0.1, 0.2, 0.3, ...] (Flat list)
            # This automatically uses task_type="retrieval_query"
            return await cls._base_embeddings.aembed_query(texts[0])
        
        # 2. Use aembed_documents for PDF chunks
        # Result: [[0.1, ...], [0.2, ...]] (List of lists)
        # This automatically uses task_type="retrieval_document"
        return await cls._base_embeddings.aembed_documents(texts)
