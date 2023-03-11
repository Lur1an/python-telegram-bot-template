from typing import AsyncIterator, TypeVar, Optional
from typing import Generic, Callable

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.results import InsertOneResult
from src.db.encoders import jsonable_encoder

from src.db.models import MongoEntity

Entity = TypeVar("Entity", bound=MongoEntity)


class BaseDAO(Generic[Entity]):
    col: AsyncIOMotorCollection
    factory: Callable[[dict], Entity]

    async def list(self) -> AsyncIterator[Entity]:
        async for entity in self.col.find():
            yield self.factory(**entity)

    async def insert_one(self, entity: Entity) -> InsertOneResult:
        return await self.col.insert_one(jsonable_encoder(entity))

    async def find_by_id(self, id: str) -> Optional[Entity]:
        result = await self.col.find_one({"_id": id})
        if result:
            return self.factory(**result)

    async def exists(self, **kwargs) -> bool:
        return await self.col.count_documents(filter=kwargs)
