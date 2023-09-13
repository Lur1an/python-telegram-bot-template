from abc import abstractmethod
from typing import Any, AsyncIterator, TypeVar, Optional, ClassVar
from typing import Generic, Callable

from bson import ObjectId
from pydantic import BaseModel, Field
from pymongo.results import InsertOneResult, UpdateResult

from src.db.encoders import jsonable_encoder

class AsyncMongoCollection:
    __slots__ = ["_collection"]

    def __init__(self, collection):
        self._collection = collection

    def __getattr__(self, name):
        return getattr(self._collection, name)

class AsyncMongoDatabase:
    _db: Any

    def __init__(self, db):
        self._db = db

    def get_collection(self, collection_name: str) -> Any:
        return self._db[collection_name]


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
    __slots__ = ["col", "factory"]
    __collection__: ClassVar[str]

    col: AsyncMongoCollection
    factory: type[Entity]


    @abstractmethod
    async def _create_indexes(self):
        pass

    @staticmethod
    async def create_all_indexes(db: AsyncMongoDatabase):
        for dao in [DAOCls(db) for DAOCls in BaseDAO.__subclasses__()]:
            await dao._create_indexes()

    def __init__(self, db: AsyncMongoDatabase):
        assert self.factory
        assert self.__collection__
        self.col = db.get_collection(self.__collection__)

    async def list(self, **filters) -> AsyncIterator[Entity]:
        async for entity in self.col.find(filter=filters):
            yield self.factory(**entity)

    async def insert(self, entity: Entity) -> InsertOneResult:
        return await self.col.insert_one(jsonable_encoder(entity))

    async def update(self, entity: Entity) -> UpdateResult:
        return await self.col.update_one({"_id": entity.id}, {"$set": jsonable_encoder(entity)})

    async def find_by_id(self, id: str) -> Optional[Entity]:
        result = await self.col.find_one({"_id": id})
        if result:
            return self.factory(**result)

    async def exists(self, **filters) -> bool:
        return await self.col.count_documents(filter=filters) != 0
