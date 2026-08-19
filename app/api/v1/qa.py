import json
import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.qa import AnswerResponse, QuestionRequest, SourceChunk
from app.services.llm import LLMService
from app.services.qa import QAService

logger = logging.getLogger(__name__)

router = APIRouter()

NO_CONTEXT_ANSWER = "I couldn't find any relevant info in that PDF."


def _to_source_chunks(chunks) -> list[SourceChunk]:
    return [SourceChunk(**asdict(c)) for c in chunks]


@router.post("/", response_model=AnswerResponse, status_code=status.HTTP_200_OK)
@limiter.limit(settings.RATE_LIMIT_QUESTIONS_PER_HOUR)
async def ask(request: Request, payload: QuestionRequest, _: User = Depends(get_current_user)):
    """
    Ask a question to the LLM.

    Requires authentication via Bearer token.
    """
    # 1. Expand the query into 4 variations (original + 3 new ones)
    queries = await QAService.expand_query(payload.question)

    # 2. Retrieve (hybrid BM25 + vector fusion, cross-encoder re-ranked)
    context = await QAService.get_relevant_context(queries, payload.document_id)

    if not context:
        return {"queries": queries, "answer": NO_CONTEXT_ANSWER, "sources": []}

    # 3. Generate
    answer = await LLMService.answer_question(payload.question, context, payload.model)

    return {"queries": queries, "answer": answer, "sources": _to_source_chunks(context)}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
@limiter.limit(settings.RATE_LIMIT_QUESTIONS_PER_HOUR)
async def ask_stream(request: Request, payload: QuestionRequest, _: User = Depends(get_current_user)):
    """
    Ask a question and stream the answer via Server-Sent Events.

    Requires authentication via Bearer token (sent as a normal Authorization
    header — this is a POST consumed via fetch()/ReadableStream, not a native
    EventSource, since EventSource can't set custom headers).

    Event sequence: "queries" -> "sources" -> one or more "token" -> "done"
    (or a terminal "error" at any point).
    """

    async def event_stream():
        try:
            queries = await QAService.expand_query(payload.question)
            yield _sse("queries", {"queries": queries})

            context = await QAService.get_relevant_context(queries, payload.document_id)
            yield _sse("sources", {"sources": [asdict(c) for c in context]})

            if not context:
                yield _sse("token", {"delta": NO_CONTEXT_ANSWER})
                yield _sse("done", {"answer": NO_CONTEXT_ANSWER, "latency_ms": 20})
                return

            async for delta, done_payload in LLMService.stream_answer(
                payload.question, context, payload.model
            ):
                if delta is not None:
                    yield _sse("token", {"delta": delta})
                else:
                    yield _sse("done", done_payload)
        except Exception as e:
            logger.exception("SSE stream error")
            yield _sse("error", {"detail": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
