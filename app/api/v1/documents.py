from fastapi import APIRouter, File, UploadFile, status, HTTPException

from app.schemas.document import DocumentResponse
from app.services.documents import DocumentService
from app.utils.file_parser import Parser


router = APIRouter()


@router.get("/", response_model=list[DocumentResponse])
async def list_my_documents():
    """
    Retrieve all documents uploaded by the current user.
    """
    return []


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    # current_user = Depends(get_current_user) # Placeholder for auth
):
    """
    Upload a document, save metadata to MongoDB, and start the AI embedding process.
    """
    # 1. Validate file extension
    allowed_extensions = ["pdf", "txt", "docx"]
    extension = file.filename.split(".")[-1].lower()
    content = await file.read()
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Extension '{extension}' not allowed. Use PDF, TXT, or DOCX."
        )

    # 2. Save document's metadata to MongoDB via Service
    doc = await DocumentService.create_document(
        filename=file.filename,
        content_type=file.content_type,
        size=len(content),
    )

    # 3. Parse content
    match extension:
        case "pdf":
            raw_text = Parser.from_pdf(content)
        case "txt":
            raw_text = Parser.from_txt(content)
        case "docx":
            raw_text = Parser.from_docx(content)

    # 4. Split the raw text into chunks and store them in MongoDB referencing their parent's id
    await DocumentService.create_chunks(raw_text=raw_text, parent_id=doc["_id"])
    
    return doc
