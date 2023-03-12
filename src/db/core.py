from typing import AsyncIterator, TypeVar, Optional, ClassVar
from typing import Generic, Callable

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from pymongo.results import InsertOneResult, UpdateResult

from src.db.encoders import jsonable_encoder


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class MongoEntity(BaseModel):
    mongo_id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    @property
    def id(self) -> str:
        return str(self.mongo_id)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str,
        }


Entity = TypeVar("Entity", bound=MongoEntity)


class BaseDAO(Generic[Entity]):
    col: AsyncIOMotorCollection
    factory: Callable[[dict], Entity]
    __collection__: ClassVar[str]

    def __init__(self, db: AsyncIOMotorDatabase):
        assert self.factory
        assert self.__collection__
        self.col = db[self.__collection__]

    async def list(self) -> AsyncIterator[Entity]:
        async for entity in self.col.find():
            yield self.factory(**entity)

    async def insert(self, entity: Entity) -> InsertOneResult:
        return await self.col.insert_one(jsonable_encoder(entity))

    async def update(self, entity: Entity) -> UpdateResult:
        return await self.col.update_one({"_id": entity.id}, {"$set": jsonable_encoder(entity)})

    async def find_by_id(self, id: str) -> Optional[Entity]:
        result = await self.col.find_one({"_id": id})
        if result:
            return self.factory(**result)

    async def exists(self, **kwargs) -> bool:
        return await self.col.count_documents(filter=kwargs)

