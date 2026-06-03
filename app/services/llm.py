import logging
import time

from app.services.llm_factory import get_llm_for_model
from app.core.metrics import record_llm_metrics

logger = logging.getLogger(__name__)


def _extract_token_usage(response) -> dict:
    """Extract token usage from LLM response metadata."""
    usage = {}
    metadata = getattr(response, "response_metadata", {}) or {}

    # OpenAI/DeepSeek format
    if "token_usage" in metadata:
        token_usage = metadata["token_usage"]
        usage["prompt_tokens"] = token_usage.get("prompt_tokens")
        usage["completion_tokens"] = token_usage.get("completion_tokens")
        usage["total_tokens"] = token_usage.get("total_tokens")
    # Gemini format
    elif "usage_metadata" in metadata:
        usage_metadata = metadata["usage_metadata"]
        usage["prompt_tokens"] = usage_metadata.get("prompt_token_count")
        usage["completion_tokens"] = usage_metadata.get("candidates_token_count")
        usage["total_tokens"] = usage_metadata.get("total_token_count")

    return usage


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

        start_time = time.perf_counter()
        response = await llm.ainvoke(prompt)
        latency_ms = (time.perf_counter() - start_time) * 1000

        token_usage = _extract_token_usage(response)
        await record_llm_metrics(
            model=model_name,
            method="answer_question",
            latency_ms=latency_ms,
            **token_usage,
        )

        return response.content
