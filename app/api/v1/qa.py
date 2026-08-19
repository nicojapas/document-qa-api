import asyncio
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
from app.utils.sse import sse, sse_padding

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


@router.post("/stream")
@limiter.limit(settings.RATE_LIMIT_QUESTIONS_PER_HOUR)
async def ask_stream(request: Request, payload: QuestionRequest, _: User = Depends(get_current_user)):
    """
    Ask a question and stream the answer via Server-Sent Events.

    Requires authentication via Bearer token (sent as a normal Authorization
    header — this is a POST consumed via fetch()/ReadableStream, not a native
    EventSource, since EventSource can't set custom headers).

    Event sequence: "queries" -> "retrieval_stage" (one per "vector" / "bm25"
    / "fuse" / "rerank", as retrieval actually reaches them) -> "sources" ->
    one or more "token" -> "done" (or a terminal "error" at any point).
    """

    async def event_stream():
        try:
            yield sse_padding()

            queries = await QAService.expand_query(payload.question)
            yield sse("queries", {"queries": queries})

            # get_relevant_context runs as a background task so its on_stage
            # callback (invoked *inside* retrieve(), mid-call) can report
            # progress through a queue while this generator concurrently
            # drains it and yields each stage the moment it happens, instead
            # of only finding out about all of them after retrieval returns.
            stage_queue: asyncio.Queue[str | None] = asyncio.Queue()

            async def on_stage(stage: str) -> None:
                await stage_queue.put(stage)

            async def run_retrieval():
                try:
                    return await QAService.get_relevant_context(
                        queries, payload.document_id, on_stage=on_stage
                    )
                finally:
                    await stage_queue.put(None)

            retrieval_task = asyncio.create_task(run_retrieval())
            try:
                while True:
                    stage = await stage_queue.get()
                    if stage is None:
                        break
                    yield sse("retrieval_stage", {"stage": stage})

                context = await retrieval_task
            finally:
                # If the client disconnects (or an earlier step raised) while
                # retrieval is still running, don't leave it going in the
                # background — cancel it.
                if not retrieval_task.done():
                    retrieval_task.cancel()

            yield sse("sources", {"sources": [asdict(c) for c in context]})

            if not context:
                yield sse("token", {"delta": NO_CONTEXT_ANSWER})
                yield sse("done", {"answer": NO_CONTEXT_ANSWER, "latency_ms": 20})
                return

            async for delta, done_payload in LLMService.stream_answer(
                payload.question, context, payload.model
            ):
                if delta is not None:
                    yield sse("token", {"delta": delta})
                else:
                    yield sse("done", done_payload)
        except Exception as e:
            logger.exception("SSE stream error")
            yield sse("error", {"detail": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
