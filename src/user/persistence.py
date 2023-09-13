from typing import Optional
from typing_extensions import override

from src.db.core import MongoEntity, BaseDAO


class User(MongoEntity):
    telegram_id: int
    telegram_username: str | None
    is_bot: bool


class UserDAO(BaseDAO[User]):
    __collection__ = "users"
    factory = User

    @override
    async def _create_indexes(self):
        await self.col.create_index("telegram_id", unique=True)

    async def find_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.col.find_one({"telegram_id": telegram_id})
        if result is not None:
            return self.factory(**result)
