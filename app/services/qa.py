import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from app.db.session import db
from app.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

class QAService:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=settings.GEMINI_AI_API_KEY)

    @classmethod
    async def expand_query(cls, question: str) -> list[str]:
        prompt = f"""
        You are an AI language model assistant. Your task is to generate 3 
        different versions of the given user query to retrieve relevant documents from a vector database. 
        By generating multiple perspectives on the user query, your goal is to help the user 
        overcome some of the limitations of distance-based similarity search. 
        Provide these alternative versions separated by newlines.
        
        Original query: {question}
        """
        response = await cls.llm.ainvoke(prompt)
        # Split by newline and add the original question to the list
        queries = [question] + response.content.strip().split("\n")
        
        return [q.strip() for q in queries if q.strip()]

    @classmethod
    async def get_relevant_context(cls, queries: list[str], doc_id: str) -> list[list[str]]:
        logger.info(f"Searching for doc_id: {doc_id}")
        logger.info(f"Number of queries: {len(queries)}")
        all_context = []

        for q in queries:
            # 2. Embed each variation
            query_vector = await EmbeddingService.generate_embeddings([q], is_query=True)
            logger.info(f"Generated embedding with {len(query_vector)} dimensions")

            # 3. Search MongoDB for each variation
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_vector,
                        "numCandidates": 50,
                        "limit": 3,
                        "filter": {
                            "parent_doc_id": doc_id
                        }
                    }
                }
            ]
            cursor = await db.chunks.aggregate(pipeline)
            results = await cursor.to_list(length=3)
            logger.info(f"Query '{q[:50]}...' returned {len(results)} results")

            all_context.extend([res["text"] for res in results])

        # 4. Remove duplicates (different queries might find the same chunk)
        logger.info(f"Total unique context chunks: {len(set(all_context))}")
        return list(set(all_context))
