from fastapi import APIRouter, File, UploadFile, status, HTTPException, Request

from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import db
from app.schemas.document import DocumentInDB, DocumentResponse, DocumentStatus
from app.services.documents import DocumentService
from app.utils.file_parser import Parser


router = APIRouter()


@router.get("/", response_model=list[DocumentResponse])
async def list_my_documents():
    """
    Retrieve all documents from the database.
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
    # current_user = Depends(get_current_user) # Placeholder for auth
) -> DocumentResponse:
    """
    Upload a document, save metadata to MongoDB, and start the AI embedding process.
    """
    # 0. Check global document limit (prevents database bloat)
    doc_count = await db.documents.count_documents({})
    if doc_count >= settings.MAX_DOCUMENTS_TOTAL:
        raise HTTPException(
            status_code=429,
            detail=f"Demo limit reached: maximum {settings.MAX_DOCUMENTS_TOTAL} documents allowed. "
                   "This is a portfolio project with limited storage."
        )

    # 1. Validate file extension
    allowed_extensions = ["pdf", "txt", "docx"]
    extension = file.filename.split(".")[-1].lower()
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Extension '{extension}' not allowed. Use PDF, TXT, or DOCX."
        )

    # 2. Read and validate file size
    content = await file.read()
    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB."
        )

    # 3. Save document's metadata to MongoDB via Service
    doc = await DocumentService.create_document(
        filename=file.filename,
        content_type=file.content_type,
        size=len(content),
    )

    # 4. Parse content and create chunks
    try:
        match extension:
            case "pdf":
                raw_text = Parser.from_pdf(content)
            case "txt":
                raw_text = Parser.from_txt(content)
            case "docx":
                raw_text = Parser.from_docx(content)

        # 5. Split the raw text into chunks and store them in MongoDB referencing their parent's id
        await DocumentService.create_chunks(raw_text=raw_text, parent_id=doc.id)

        # 6. Mark document as ready
        await DocumentService.update_status(doc.id, DocumentStatus.ready)
        doc.status = DocumentStatus.ready

    except Exception:
        await DocumentService.update_status(doc.id, DocumentStatus.failed)
        raise

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        created_at=doc.created_at,
    )
