import logging
import time
from typing import AsyncGenerator, TYPE_CHECKING

from app.services.llm_factory import get_llm_for_model
from app.core.metrics import record_llm_metrics

if TYPE_CHECKING:
    from app.services.retrieval import RetrievedChunk

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


def _extract_token_usage_from_chunk(chunk) -> dict:
    """
    Extract token usage from the final chunk of a streamed response.

    Gemini populates usage_metadata on the final AIMessageChunk automatically.
    ChatOpenAI-based providers (openai/deepseek/modal) only do this when
    constructed with stream_usage=True (see llm_factory.py).
    """
    usage_metadata = getattr(chunk, "usage_metadata", None)
    if usage_metadata:
        return {
            "prompt_tokens": usage_metadata.get("input_tokens"),
            "completion_tokens": usage_metadata.get("output_tokens"),
            "total_tokens": usage_metadata.get("total_tokens"),
        }
    return _extract_token_usage(chunk)


def _build_prompt(question: str, context: list["RetrievedChunk"]) -> str:
    context_text = "\n\n".join(c.text for c in context)
    return f"""
        Answer the question based ONLY on the following context.
        If the answer is not in the context, say you don't know.

        Context: {context_text}

        Question: {question}
        """


class LLMService:
    @classmethod
    async def answer_question(
        cls, question: str, context: list["RetrievedChunk"], model: str | None = None
    ):
        llm = get_llm_for_model(model)
        prompt = _build_prompt(question, context)
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

    @classmethod
    async def stream_answer(
        cls, question: str, context: list["RetrievedChunk"], model: str | None = None
    ) -> AsyncGenerator[tuple[str | None, dict | None], None]:
        """
        Stream the answer token-by-token.

        Yields (delta, None) for each streamed piece of content, then a final
        (None, done_payload) once generation completes, where done_payload
        carries the full answer text plus latency/token metrics.
        """
        llm = get_llm_for_model(model)
        prompt = _build_prompt(question, context)
        model_name = getattr(llm, "model_name", getattr(llm, "model", "unknown"))

        start_time = time.perf_counter()
        pieces: list[str] = []
        final_chunk = None

        async for chunk in llm.astream(prompt):
            if chunk.content:
                pieces.append(chunk.content)
                yield chunk.content, None
            final_chunk = chunk

        latency_ms = (time.perf_counter() - start_time) * 1000
        token_usage = _extract_token_usage_from_chunk(final_chunk) if final_chunk else {}

        await record_llm_metrics(
            model=model_name,
            method="answer_question_stream",
            latency_ms=latency_ms,
            **token_usage,
        )

        yield None, {
            "answer": "".join(pieces),
            "latency_ms": round(latency_ms, 1),
            **token_usage,
        }
