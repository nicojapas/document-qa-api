from fastapi import FastAPI
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION
)

# Include the aggregate router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to Document QA API. Visit /docs for Swagger."}
