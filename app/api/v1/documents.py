from fastapi import APIRouter, File, UploadFile, status, HTTPException

from app.schemas.document import DocumentResponse


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
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Extension '{extension}' not allowed. Use PDF, TXT, or DOCX."
        )

    # 2. CALL SERVICE (Point 3)
    # For now, we simulate a successful database record
    # Later, you will do: doc = await DocumentService.create(file)
    mock_response = {
        "_id": "65a6f1...", # Simulating MongoDB ID
        "filename": file.filename,
        "content_type": file.content_type,
        "size": 0, # We'd calculate this
        "status": "processing",
        "created_at": "2026-01-16T12:00:00"
    }
    
    return mock_response