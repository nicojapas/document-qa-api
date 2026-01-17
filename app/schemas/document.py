from pydantic import BaseModel

class DocumentBase(BaseModel):
    pass

class DocumentDB(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    pass