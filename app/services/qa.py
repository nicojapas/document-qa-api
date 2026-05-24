import logging
from app.services.embeddings import EmbeddingService
from app.services.llm_factory import get_llm
from app.services.vector_store import get_vector_store
from app.core.config import settings

logger = logging.getLogger(__name__)


class QAService:
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
        llm = get_llm()
        model_name = getattr(llm, "model_name", getattr(llm, "model", "unknown"))
        logger.info(f"Chat invoked: provider={settings.LLM_PROVIDER}, model={model_name}, method=expand_query")
        response = await llm.ainvoke(prompt)
        # Split by newline and add the original question to the list
        queries = [question] + response.content.strip().split("\n")
        
        return [q.strip() for q in queries if q.strip()]

    @classmethod
    async def get_relevant_context(cls, queries: list[str], doc_id: str) -> list[str]:
        logger.debug(f"Searching for doc_id: {doc_id}")
        logger.debug(f"Number of queries: {len(queries)}")

        vector_store = get_vector_store()
        all_context = []

        for q in queries:
            query_vector = await EmbeddingService.generate_embeddings([q], is_query=True)
            logger.debug(f"Generated embedding with {len(query_vector)} dimensions")

            results = await vector_store.search(query_vector, doc_id, top_k=3)
            logger.debug(f"Query '{q[:50]}...' returned {len(results)} results")

            all_context.extend(results)

        # Remove duplicates (different queries might find the same chunk)
        unique_context = list(set(all_context))
        logger.debug(f"Total unique context chunks: {len(unique_context)}")
        return unique_context
