import logging

from fastapi import APIRouter, Depends, File, UploadFile, status, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import db
from app.models.user import User
from app.schemas.document import DocumentInDB, DocumentResponse, DocumentStatus
from app.services.documents import DocumentService
from app.services.embeddings import EMBEDDING_MODEL
from app.utils.file_parser import Parser
from app.utils.sse import sse, sse_padding

VECTOR_STORE_LABELS = {"mongodb": "MongoDB Atlas", "faiss": "FAISS (local)"}


router = APIRouter()


async def _check_document_limit() -> None:
    doc_count = await db.documents.count_documents({})
    if doc_count >= settings.MAX_DOCUMENTS_TOTAL:
        raise HTTPException(
            status_code=429,
            detail=f"Demo limit reached: maximum {settings.MAX_DOCUMENTS_TOTAL} documents allowed. "
                   "This is a portfolio project with limited storage."
        )


def _validate_extension(filename: str) -> str:
    allowed_extensions = ["pdf", "txt", "docx"]
    extension = filename.split(".")[-1].lower()
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Extension '{extension}' not allowed. Use PDF, TXT, or DOCX."
        )
    return extension


def _validate_size(content: bytes) -> None:
    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB."
        )


def _parse_text(extension: str, content: bytes) -> str:
    match extension:
        case "pdf":
            return Parser.from_pdf(content)
        case "txt":
            return Parser.from_txt(content)
        case "docx":
            return Parser.from_docx(content)


@router.get("/", response_model=list[DocumentResponse])
async def list_my_documents(_: User = Depends(get_current_user)):
    """
    Retrieve all documents from the database.

    Requires authentication via Bearer token.
    """
    documents = await DocumentService.list_documents()
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            status=doc.status,
            created_at=doc.created_at,
        )
        for doc in documents
    ]


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_UPLOADS_PER_HOUR)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
) -> DocumentResponse:
    """
    Upload a document, save metadata to MongoDB, and start the AI embedding process.

    Requires authentication via Bearer token.
    """
    await _check_document_limit()
    extension = _validate_extension(file.filename)

    content = await file.read()
    _validate_size(content)

    doc = await DocumentService.create_document(
        filename=file.filename,
        content_type=file.content_type,
        size=len(content),
    )

    try:
        raw_text = _parse_text(extension, content)
        await DocumentService.create_chunks(raw_text=raw_text, parent_id=doc.id)

        await DocumentService.update_status(doc.id, DocumentStatus.ready)
        doc.status = DocumentStatus.ready

    except Exception as e:
        logger.error(f"Failed to process document {doc.id}: {e}")
        await DocumentService.update_status(doc.id, DocumentStatus.failed)
        raise

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        created_at=doc.created_at,
    )


@router.post("/stream")
@limiter.limit(settings.RATE_LIMIT_UPLOADS_PER_HOUR)
async def upload_document_stream(
    request: Request,
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    """
    Upload a document and stream ingestion progress via Server-Sent Events.

    Requires authentication via Bearer token (sent as a normal Authorization
    header — this is a POST consumed via fetch()/ReadableStream, not a native
    EventSource, since EventSource can't set custom headers).

    Event sequence: "received" -> "split" -> "embed" -> "store" -> "done"
    (or a terminal "error" at any point).
    """
    await _check_document_limit()
    extension = _validate_extension(file.filename)

    content = await file.read()
    _validate_size(content)

    filename = file.filename
    content_type = file.content_type

    async def event_stream():
        doc = None
        try:
            yield sse_padding()

            doc = await DocumentService.create_document(
                filename=filename,
                content_type=content_type,
                size=len(content),
            )
            yield sse("received", {"id": doc.id, "filename": doc.filename})

            raw_text = _parse_text(extension, content)
            chunks = DocumentService.split_text(raw_text, doc.id)
            yield sse("split", {"chunk_count": len(chunks)})

            vectors = await DocumentService.embed_chunks(chunks)
            yield sse("embed", {"chunk_count": len(chunks), "model": EMBEDDING_MODEL})

            await DocumentService.store_chunks(chunks, vectors, doc.id)
            backend = VECTOR_STORE_LABELS.get(settings.VECTOR_STORE.lower(), settings.VECTOR_STORE)
            yield sse("store", {"chunk_count": len(chunks), "backend": backend})

            await DocumentService.update_status(doc.id, DocumentStatus.ready)
            yield sse("done", {
                "id": doc.id,
                "filename": doc.filename,
                "status": DocumentStatus.ready.value,
                "created_at": doc.created_at.isoformat(),
            })
        except Exception as e:
            logger.error(f"Failed to process document {doc.id if doc else '?'}: {e}")
            if doc is not None:
                await DocumentService.update_status(doc.id, DocumentStatus.failed)
            yield sse("error", {"detail": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
