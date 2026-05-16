from app.services.llm_factory import get_llm
from app.core.config import settings


class LLMService:
    llm = get_llm()

    @classmethod
    async def answer_question(cls, question: str, context: list[str]):
        context_text = "\n\n".join(context)
        prompt = f"""
        Answer the question based ONLY on the following context.
        If the answer is not in the context, say you don't know.

        Context: {context_text}

        Question: {question}
        """
        model_name = getattr(cls.llm, "model_name", getattr(cls.llm, "model", "unknown"))
        print(f"[LLM] Chat invoked: provider={settings.LLM_PROVIDER}, model={model_name}, method=answer_question")
        response = await cls.llm.ainvoke(prompt)
        
        return response.content
