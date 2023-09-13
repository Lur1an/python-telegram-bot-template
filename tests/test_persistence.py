from motor.motor_asyncio import AsyncIOMotorClient
from src.db.core import AsyncMongoDatabase, BaseDAO
import pytest_asyncio
from src.user.persistence import User, UserDAO


@pytest_asyncio.fixture
async def db():
    mongo_client = AsyncIOMotorClient("mongodb://root:root@localhost:27017")
    mongo_client.drop_database("test")
    database = AsyncMongoDatabase(mongo_client["test"])
    await BaseDAO.create_all_indexes(database)
    yield database

async def test_user_insert(db):
    dao = UserDAO(db)
    user = User(
        telegram_id=123,
        telegram_username="test",
        is_bot=False
    )
    result = await dao.insert(user)
    assert result.inserted_id
    queried_user = await dao.find_by_id(result.inserted_id)
    assert queried_user == user

