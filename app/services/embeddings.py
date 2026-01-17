from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings

class EmbeddingService:
    @classmethod
    async def generate_embeddings(cls, texts: list[str]):
        # LangChain wraps the Gemini API
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            api_key=settings.GEMINI_AI_API_KEY,
            task_type="RETRIEVAL_DOCUMENT"
        )
        
        return await embeddings.aembed_documents(texts)

