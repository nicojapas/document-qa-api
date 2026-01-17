from app.core.config import settings
from pymongo import AsyncMongoClient
from pymongo.server_api import ServerApi


# Initialize client
client = AsyncMongoClient(
    settings.MONGODB_URL,
    server_api=ServerApi('1')
)
db = client[settings.DATABASE_NAME]