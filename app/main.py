from fastapi import FastAPI
from app.api.v1.api import api_router

app = FastAPI()


app = FastAPI(
    title="Document QA API",
    description="AI-powered RAG API with FastAPI and MongoDB",
    version="1.0.0"
)

# Include the aggregate router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to Document QA API. Visit /docs for Swagger."}
