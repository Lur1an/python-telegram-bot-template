# python-telegram-bot-template
This repository serves as a template to create new [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
applications, their python wrapper over the Telegram API is amazing and enables very smooth programming for bots. 
### Foreword
I made this template to provide an implementation for a few things that I always ended up implementing in my bot projects,
the custom `ApplicationContext` to have typing support for `context.bot_data, context.chat_data, context.user_data`,decorators/wrappers for handlers to cut down on a bit of verbose boilerplate.

### Configuration
The app gets its configuration from environment variables that are defined in the classes extending `pydantic.BaseSettings` in `settings.py`
```python
from pydantic import BaseSettings

class DBSettings(BaseSettings):
    MONGODB_CONNECTION_URL: str
    MONGODB_DB: str


class TelegramSettings(BaseSettings):
    BOT_TOKEN: str


class Settings(TelegramSettings, DBSettings):
    pass


settings = Settings()

```
### How to persist entities
For the persistence layer of the project I created two main template classes to extend, `MongoEntity` and `BaseDao`,
both live in `db.core`.
```python
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
```
Since `Generic[Entity]` is just a type helper, to actually build the objects from the dictionaries returned by the MongoDB queries you need to set the `factory` field to the actual class, and to get the collection from which you want to query the entities themselves you need to set the `__collection__` field of your class, the `__init__` method will make sure of that, failing the assertion otherwise. As I am not too familiar with python internals and metaprogramming I would love and appreciate any advice to smooth out this persistence layer.

Sample implementation:
```python
class User(MongoEntity):
    username: str

class UserDAO(BaseDAO[User]):
    __collection__ = "users"
    factory = User
```
With these few lines of code you now have access to the default CRUD implementations of the BaseDAO class, with type hints!
To add functionality look up the *[Motor documentation](https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_collection.html)*

```python
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
```
The data is modeled using pydantic. Any object that will be persisted to the database has to extend `MongoEntity`,
the `@property` implementation of `id` is needed because queries don't automatically convert between `ObjectId` and string. [To learn more about the power of pydantic check out their docs as well!](https://docs.pydantic.dev/)
### Application State
When you use python-telegram-bot you have access to 3 shared `dict` objects on your `context`:
1. `context.user_data`, this object is shared between all handlers that interact with updates from the same user
2. `context.chat_data`, shared between all updates for the same chat
3. `context.bot_data`, this is shared by all handlers and is useful to keep track of your shared application state

Working with raw dicts is error prone, that's why python-telegram-bot let's you define your own `CallbackContext` to replace the usual `ContextTypes.DEFAULT`. 
```python
class BotData:
    pass

class ChatData:
    pass

class UserData:
    pass

class ApplicationContext(CallbackContext[ExtBot, UserData, ChatData, BotData]):
    # Define custom @property methods here that interact with your context
    pass

```
You will find these classes in the `bot.common` module in `context.py`, you can edit the three classes above to define the state in your application depending on the context, the `ApplicationContext` class itself is used in the type signature for the context of your handlers and you can also define useful `@property` methods on it as well.

#### How are my Context classes initialized if I am only passing them as type-hints? 
To make the framework instantiate your custom objects instead of the usual dictionaries they are passed as a `ContextTypes` object to your `ApplicationBuilder`, the template takes care of this. The `Application` object itself is build inside of `bot.application`, that's also where you will need to register your handlers, either in the `on_startup` method or on the application object.
```python
context_types = ContextTypes(
    context=ApplicationContext,
    chat_data=ChatData,
    bot_data=BotData,
    user_data=UserData
)

application = ApplicationBuilder()
    .token(settings.BOT_TOKEN)
    .context_types(context_types)
    .arbitrary_callback_data(True)
    .post_init(on_startup)
    .build()
```
Now all logic defined in custom `__init__` methods will be executed and default instance variables will instantiated.

