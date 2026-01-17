from app.db.session import db
from app.schemas.document import DocumentDB
from datetime import datetime

class DocumentService:
    @staticmethod
    async def create_document(filename: str, content_type: str, size: int):
        doc_data = {
            "filename": filename,
            "content_type": content_type,
            "size": size,
            "status": "processing",
            "created_at": datetime.now()
        }
        # Insert into MongoDB
        result = await db.documents.insert_one(doc_data)
        
        # Return the created doc with its new _id
        doc_data["_id"] = str(result.inserted_id)

        return doc_data
