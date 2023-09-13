from motor.motor_asyncio import AsyncIOMotorClient
from src.db.core import AsyncMongoDatabase
from src.settings import settings

mongo_client = AsyncIOMotorClient(settings.MONGODB_CONNECTION_URL)
db = AsyncMongoDatabase(mongo_client[settings.MONGODB_DB])
