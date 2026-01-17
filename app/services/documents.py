from app.db.session import db
from datetime import datetime

from app.services.embeddings import EmbeddingService
from app.utils.text_splitter import split_and_process_text

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

    @staticmethod
    async def create_chunks(raw_text: str, parent_id: str):
        chunks = split_and_process_text(raw_text)
        
        # Generate all embeddings in efficient batches
        vectors = await EmbeddingService.generate_embeddings(chunks)

        chunk_documents = [
            {
                "parent_doc_id": parent_id,
                "index": index,
                "text": text,
                "embedding": vectors[index],
                "create_at": datetime.now()
            }
            for index, text in enumerate(chunks)
        ]
        
        if chunk_documents:
            await db.chunks.insert_many(chunk_documents)
