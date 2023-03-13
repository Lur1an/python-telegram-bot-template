from typing import Optional

from src.db.core import MongoEntity, BaseDAO


class User(MongoEntity):
    telegram_id: int
    telegram_username: str
    is_bot: bool


class UserDAO(BaseDAO[MongoEntity]):
    __collection__ = "users"
    factory = User

    async def find_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.col.find_one({"telegram_id": telegram_id})
        if result is not None:
            return User(**result)
