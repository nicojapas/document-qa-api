import logging

from app.services.llm_factory import get_llm_for_model

logger = logging.getLogger(__name__)


class LLMService:
    @classmethod
    async def answer_question(cls, question: str, context: list[str], model: str | None = None):
        llm = get_llm_for_model(model)
        context_text = "\n\n".join(context)
        prompt = f"""
        Answer the question based ONLY on the following context.
        If the answer is not in the context, say you don't know.

        Context: {context_text}

        Question: {question}
        """
        model_name = getattr(llm, "model_name", getattr(llm, "model", "unknown"))
        logger.info(f"Chat invoked: model={model_name}, method=answer_question")
        response = await llm.ainvoke(prompt)

        return response.content
