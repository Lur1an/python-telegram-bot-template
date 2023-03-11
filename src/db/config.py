from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.settings import settings

mongo_client = AsyncIOMotorClient(settings.MONGODB_CONNECTION_URL)
db: AsyncIOMotorDatabase = mongo_client[settings.MONGODB_DB]
