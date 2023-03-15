# python-telegram-bot-template

This repository serves as a template to create
new [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
applications, their python wrapper over the Telegram API is amazing and enables very smooth programming for bots. It
doesn't however provide ***defaults*** for persistence, state management and other shortcuts that are necessary for a
maintainable and growable software architecture.

This template is mostly meant for projects that start with quite a bit of complexity and whose requirements are going to
evolve as time passes.

### Foreword

I made this template to provide an implementation for a few things that I always ended up implementing in my *telegram
bot* projects, custom `ApplicationContext` for `context.bot_data, context.chat_data, context.user_data` typing,
decorators/wrappers for handlers to cut down on a bit of boilerplate and implement common behaviours. This will take the
mind off technicalities and instead help put your focus where it belongs, on the project.

On a sidenote:  the code inside of `encoders.py` for `jsonable_encoder` is from [tiangolo/fastapi](https://github.com/tiangolo/fastapi)
### Run the Bot

To run the bot you just have to execute `main.py` with the following environment variables set:

1. `MONGODB_CONNECTION_URL` needed to conntect to your database, feel free to swap out the persistence layer with
   anything you prefer or to remove it entirely, MongoDB together with their atlas-cloud database is a nice way to get
   started prototyping your small projects. *In hindsight* I should have just used SQLite with SQLAlchemy, this would
   allow anyone that pulls the template to just start it up with a bot token.
2. `MONGODB_DATABASE` name of your database
3. `BOT_TOKEN`you can get one from ***[Botfather](https://t.me/botfather)***

### Devops and Dependency management

```yaml
name: CI
on:
  push:
    branches: [ "master" ]
jobs:
  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Poetry
        uses: snok/install-poetry@v1

      - name: create requirements
        run: poetry export --without-hashes --format=requirements.txt > requirements.txt

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_PASSWORD }}
      - name: Build and push image
        uses: docker/build-push-action@v3
        with:
          context: .
          push: true
          tags: ${{ secrets.DOCKERHUB_TARGET }}
```

This simple CI script will get your pipeline started, it uses poetry to export your `pyproject.toml` dependencies as
a `requirements.txt` file that is needed for the Docker build, then proceeds to push the built image to your docker
repository, afterwards any Continuous Deployment solution may take over from there.
Once you have started implementing some business logic you can add a `poetry run pytest` step to the pipeline
***(remember to poetry install first)***.

The template ships with ***[poetry](https://python-poetry.org/)***, if you don't want to use this just
delete `pyproject.toml, poetry.lock` and keep a `requirements.txt` file in your project for the docker build.

### Configuration

The app gets its configuration from environment variables that are defined in the classes
extending `pydantic.BaseSettings` in `settings.py`

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

    @abstractmethod
    async def _create_indexes(self):
        pass

    @staticmethod
    async def create_all_indexes():
        for dao in [d(db) for d in BaseDAO.__subclasses__()]:
            await dao._create_indexes()
                
    def __init__(self, db: AsyncIOMotorDatabase):
        assert self.factory
        assert self.__collection__
        self.col = db[self.__collection__]

    async def list(self, **filters) -> AsyncIterator[Entity]:
        async for entity in self.col.find(filters=filters):
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

Since `Generic[Entity]` is just a type helper, to actually build the objects from the dictionaries returned by the
MongoDB queries you need to set the `factory` field to the actual class, and to get the collection from which you want
to query the entities themselves you need to set the `__collection__` field of your class, the `__init__` method will
make sure of that, failing the assertion otherwise. As I am not too familiar with python internals and metaprogramming I
would love and appreciate any advice to smooth out this persistence layer.

Update: I created a way to initialize all your database indexes for your collections at runtime, if you override the abstract private method `_create_indexes` in your subclasses, the `BaseDAO.create_all_indexes()` that is called on the startup method will create them.

Sample implementation:

```python
class User(MongoEntity):
    username: str


class UserDAO(BaseDAO[User]):
    __collection__ = "users"
    factory = User
```

With these few lines of code you now have access to the default CRUD implementations of the BaseDAO class, with type
hints!
To add functionality look up the
*[Motor documentation](https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_collection.html)*

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
the `@property` implementation of `id` is needed because queries don't automatically convert between `ObjectId` and
string. [To learn more about the power of pydantic check out their docs as well!](https://docs.pydantic.dev/)

### Application State

When you use python-telegram-bot you have access to 3 shared `dict` objects on your `context`:

1. `context.user_data`, this object is shared between all handlers that interact with updates from the same user
2. `context.chat_data`, shared between all updates for the same chat
3. `context.bot_data`, this is shared by all handlers and is useful to keep track of your shared application state

Working with raw dicts is error prone, that's why python-telegram-bot let's you define your own `CallbackContext` to
replace the usual `ContextTypes.DEFAULT`.

```python
class BotData:
    user_cache: Dict[int, User] = {}
    pass


class ChatData:
    pass


class UserData:
    pass


class ApplicationContext(CallbackContext[ExtBot, UserData, ChatData, BotData]):
    # Define custom @property and utility methods here that interact with your context
    def get_cached_user(self, telegram_id: int) -> Optional[User]:
        return self.bot_data.user_cache.get(telegram_id, None)

    def cache_user(self, user: User):
        self.bot_data.user_cache[user.telegram_id] = user
```

You will find these classes in the `bot.common` module in `context.py`, you can edit the three classes above to define
the state in your application depending on the context, the `ApplicationContext` class itself is used in the type
signature for the context of your handlers and you can also define useful `@property` and other utility methods on it as
well.

A quick note on the `user_cache` in the `BotData` class:

Why am I not caching the user object in the `UserData` class, such that interactions that involve the same user can
access it for examplte with `context.user_data.user`?\
You might need to invalidate/update certain `User` objects from a context outside of your user context, for example an
admin banning a user or a background job updating certain fields, since `context.bot_data` is shared between all context
instances and accessible by background jobs I decided to cache users here.

Why cache the `User` at all?\
If you have a flow that expects a lot of sequential user interactions that access the entity you might soon run into
trouble querying the database every time you get a telegram update.

Note: I still need to add a background job that periodically invalidates cached `User` objects.

#### How are my Context classes initialized if I am only passing them as type-hints?

To make the framework instantiate your custom objects instead of the usual dictionaries they are passed as
a `ContextTypes` object to your `ApplicationBuilder`, the template takes care of this. The `Application` object itself
is build inside of `bot.application`, that's also where you will need to register your handlers, either in
the `on_startup` method or on the application object.

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

### Conversation State

As you may have noticed, the three State objects that are present in the context have user, chat and global scope. A lot
of logic is implemented inside of `ConversationHandler` flows and for this custom state-management is needed, usually
inside either `chat_data` or `user_data`, as most of these flows in my experience have been on a per-user basis I have
provided a default to achieve this without having to add a new field to your `UserData` class for every
conversation-flow that you need to implement.

```python
class UserData:
    _conversation_state: Dict[Type[ConversationState], ConversationState] = {}

    def get_conversation_state(self, cls: Type[ConversationState]) -> ConversationState:
        return self._conversation_state[cls]

    def initialize_conversation_state(self, cls: Type[ConversationState]):
        self._conversation_state[cls] = cls()

    def clean_up_conversation_state(self, conversation_type: Type[ConversationState]):
        del self._conversation_state[conversation_type]
```

The `UserData` class comes pre-defined with a dictionary to hold conversation state, the type of the object
itself is used as a key to identify it, this necessitates that for a conversation state type `T` there is at most 1
active conversation ***per user*** that uses this type for its state.

To avoid leaking memory this object needs to be cleared from the dictionary when you are done with it, to take care of
initialization and cleanup I have created three decorators:

```python
def init_stateful_conversation(conversation_state_type: Type[ConversationState]):
    ...


def inject_conversation_state(conversation_state_type: Type[ConversationState]):
    ...


def cleanup_stateful_conversation(conversation_state_type: Type[ConversationState]):
    ...
```

Using these you can decorate your conversation entry/exit points, to take care of the state and also inject the object
into your function as an argument. `cleanup_stateful_conversation` also makes sure to catch any unexpected exceptions
and return `Conversation handler.END` when it finishes.

For example, let's define an entry point handler and an exit method for a conversation flow where a user needs to follow
multiple steps to fill up a `OrderRequest` object. (I will ignore the implementation details for
a `ConversationHandler`, if you want to see a good example of how this works
***[click here](https://docs.python-telegram-bot.org/en/stable/examples.conversationbot.html)***)

```python
@init_stateful_conversation(OrderRequest)
async def start_order_request(
        update: Update,
        context: ApplicationContext,
        order_request: OrderRequest
):
    ...


@inject_conversation_state(OrderRequest)
async def add_item(
        update: Update,
        context: ApplicationContext,
        order_request: OrderRequest
):
    ...


@cleanup_stateful_conversation(OrderRequest)
async def file_order(
        update: Update,
        context: ApplicationContext,
        order_request: OrderRequest
):
    # Complete the order, persist to database, send messages, etc...
    ...
```

### Utility decorators

```python
def restricted_action(is_allowed: Callable[[Update, ApplicationContext], Awaitable[Any]]):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            if await is_allowed(update, context):
                return await f(update, context)

        return wrapped

    return inner_decorator
```

This decorator is used to restrict handler access by using the function passed as parameter to the decorator to check.

```python
def delete_message_after(f: Callable[[Update, ApplicationContext], Awaitable[Any]]):
    @wraps(f)
    async def wrapper(update: Update, context: ApplicationContext):
        result = await f(update, context)
        try:
            await context.bot.delete_message(
                message_id=update.effective_message.id,
                chat_id=update.effective_chat.id
            )
        finally:
            return result

    return wrapper
```

This decorator ensures your handler ***tries*** to delete the message after finishing the
logic, `update.effective_message.delete()` from time to time throws exceptions even when it shouldn't, as
does `bot.delete_message`, this decorator is a easy and safe way to abstract this away and make sure you tried your best
to delete that message.

```python
def exit_conversation_on_exception(
        _f: Callable[[Update, ApplicationContext], Any] = None, *,
        user_message: str = "I'm sorry, something went wrong, try again or contact an Administrator."
):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Any]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            try:
                return await f(update, context)
            except Exception as e:
                log.error(f"Encountered an error while handling conversation step: {e}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=user_message
                )
                context.chat_data.conversation_data = None
                return ConversationHandler.END

        return wrapped

    if _f is None:
        return inner_decorator
    else:
        return inner_decorator(_f)
```

This decorator catches any unchecked exceptions in your handlers inside of your conversation flow that you annotate with
it and sends the poor user that had to interact with your ***(my)*** mess a message.

### CallbackQuery data injection

Arbitrary callback data is an awesome feature of *python-telegram-bot*, it increases security of your application (
callback-queries are generated on the client-side and can contain malicious payloads) and makes your development
workflow easier.

Since the smoothest interactions are through inline keyboards your application will be full of `CallbackQueryHandler`
flows. The problem is that `callback_data` does not provide a type hint for your objects, making you write the same code
over and over again to satisfy the type checker and get type hints:

```python
async def sample_handler(update: Update, context: ApplicationContext):
    my_data = cast(CustomData, context.callback_data)
    ...  # do stuff
    await update.callback_query.answer()
    # if you want you can also clear your callback data from your cache
```

I prefer using my decorator:

```python
def inject_callback_query(
        _f: Callable[[Update, ApplicationContext, CallbackDataType], Awaitable[Any]] = None, *,
        answer_query_after: bool = True,
        clear_callback_data: bool = False,
):
    def inner_decorator(f: Callable[[Update, ApplicationContext, CallbackDataType], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            converted_data = cast(CallbackDataType, update.callback_query.data)
            result = await f(update, context, converted_data)
            if answer_query_after:
                try:
                    await update.callback_query.answer()
                except Exception as e:
                    log.error(f"Failed answering callback_query: {e}")
            if clear_callback_data:
                try:
                    context.drop_callback_data(update.callback_query)
                except KeyError as e:
                    log.error(f"Failed dropping callback_query_data, couldn't find Key: {e}")

            return result

        return wrapped

    if _f is None:
        return inner_decorator
    else:
        return inner_decorator(_f)
```

Now you can write your handler like this:

```python
@inject_callback_query
async def sample_handler(update: Update, context: ApplicationContext, my_data: CustomData):
    ...  # do stuff
```

Since we are interacting with our `CustomData` type in our `CallbackQueryHandler` most of the time we only have 1
handler for this defined Callback Type and always end up writing:

```python
custom_data_callback_handler = CallbackQueryHandler(callback=sample_handler, pattern=CustomData)
```

I added another decorator to turn the wrapped function directly into a `CallbackQueryHandler`:

```python
def arbitrary_callback_query_handler(
        query_data_type: CallbackDataType, *,
        inject: bool = True,
        answer_query_after: bool = True,
        clear_callback_data: bool = False
):
    if inject:
        def inner_decorator(
                f: Callable[[Update, ApplicationContext, CallbackDataType], Awaitable[Any]]
        ) -> CallbackQueryHandler:
            decorator = inject_callback_query(
                answer_query_after=answer_query_after,
                clear_callback_data=clear_callback_data
            )
            wrapped = decorator(f)
            handler = CallbackQueryHandler(pattern=query_data_type, callback=wrapped)
            return handler

        return inner_decorator
    else:
        def inner_decorator(
                f: Callable[[Update, ApplicationContext], Awaitable[Any]]
        ) -> CallbackQueryHandler:
            if answer_query_after:
                f = answer_inline_query_after(f)
            if clear_callback_data:
                f = drop_callback_data_after(f)
            handler = CallbackQueryHandler(pattern=query_data_type, callback=f)
            return handler

        return inner_decorator

```

This will take care of instantiating your `CallbackQueryHandler`, putting this together with the above sample we can
write it like this:

```python
@arbitrary_callback_query_handler(CustomData)
async def sample_handler(update: Update, context: ApplicationContext, my_data: CustomData):
    ...  # do stuff
```

Keep in mind that this approach is a bit limited if you want to handle types of `CustomData` callback queries
differently depending on other patterns like chat or message content, python-telegram-bot lets you combine patterns
together with binary logic operators, as I have rarely used this I have not added parameters to the decorator for this
case, I might in the future. Since this is just a template you can also do it yourself for your project!

### Project Structure

I would recommend you keep your code loosely coupled and keep cohesion high, separate your modules by feature:

```
├── src
│   ├── bot
│   │   ├── application.py
│   │   ├── common
│   │   │   ├── context.py
│   │   │   └── wrappers.py
│   │   ├── __init__.py
│   ├── orders
│   │   │   ├── conversations
│   │   │   │  ├── create_order.py
│   │   │   │  ├── edit_order.py
│   │   │   ├── persistence.py
│   │   │   ├── models.py
│   │   │   ├── handlers.py
│   ├── db
│   │   ├── config.py
│   │   ├── core.py
│   │   ├── encoders.py
│   ├── __init__.py
│   ├── main.py
│   ├── resources
│   └── settings.py
└── tests
└── __init__.py
```

I added a folder `orders` that could represent a way to add a feature to interact with orders:

+ `persistence.py` can contain your class `OrderDAO` and `OrderEntity` to model your database persistence
+ `models.py` can contain other object types you need, like classes for custom callback queries or conversation state
+ `handlers.py` is where you define the handlers needed to interact with this module through the telegram api, export a
  list of handlers that you import in `application.py` and then add to the `Application` object
  through `add_handlers()`. This list of handlers has to contain all the handlers of the module
+ `conversations` contains a file for every `ConversationHandler` the module defines, since it takes a lot of code to
  define a single conversation, with it's states, state-management, fallbacks etc. a single file for every conversation
  flow seems okay.

These are just examples how the structure could look like.

### Cool wrappers

```python
def command_handler(command: str, *, allow_group: bool = False):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Coroutine[Any, Any, RT]]) -> CommandHandler:
        return CommandHandler(
            filters=None if allow_group else filters.ChatType.PRIVATE,
            command=command,
            callback=f
        )

    return inner_decorator
```

Shortcut to create command handlers, by default they are set to only work in private chats and have to be explicitly
activated for group chats.

```python
def load_user(
        _f: Callable[[Update, ApplicationContext, User], Coroutine[Any, Any, RT]] = None,
        *,
        required: bool = False,
        error_message: Optional[str] = None
):
    def inner_decorator(f: Callable[[Update, ApplicationContext, User], Coroutine[Any, Any, RT]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            user = context.get_cached_user(update.effective_user.id)
            if user is None:
                dao = UserDAO(db)
                user = await dao.find_by_telegram_id(update.effective_user.id)
                context.cache_user(user)
            if user is None and required:
                if error_message is not None:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=error_message
                    )
                return
            return await f(update, context)

        return wrapped

    return inner_decorator
```

This decorator allows you to pre-load the user before actually handling the event and avoids the usual 'check in
cache' -> 'load from database' flow, and if user is not found and you want to send a default error message you can also
set this from the decorator.

### Reducing boilerplate for [user <-> data] interactions

After programming bots for a while I always found myself using the same pattern to define actions on my entities:

```python
class DeleteItem(BaseModel):
    item: Item


delete_item_button = InlineKeyboardButton(
    text="❌ DELETE ITEM ❌",
    callback_data=DeleteItem(item=my_item)
)
reply_markup = InlineKeyboardMarkup([
    [delete_item_button]
])
```

This would create a menu with a single button, but you can imagine that there could be more, each one with its own class
for the action it represents. So I came up with this class that turns itself into a button or a single keyboard (found
myself often making single-row keyboards), I reference `__class__.__name__` to derive the button text and surround it
with an emoji if provided, turning a class like `EDIT_ITEM` into either `EDIT` or `EDIT ITEM` buttons.

```python
class CallbackButton(BaseModel):
    def to_short_button(self, *, emoji: Optional[str]) -> InlineKeyboardButton:
        text = self.__class__.__name__.split("_")[0]
        if emoji:
            text = f"{emoji} {text} {emoji}"
        return InlineKeyboardButton(text=text, callback_data=self)

    def to_button(self, *, text: Optional[str] = None, emoji: Optional[str]) -> InlineKeyboardButton:
        if text is None:
            text = (' ').join(self.__class__.__name__.split("_"))

        if emoji:
            text = f"{emoji} {text} {emoji}"
        return InlineKeyboardButton(text=text, callback_data=self)

    def to_keyboard(
            self,
            *,
            text: Optional[str] = None,
            emoji: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [self.to_button(text=text, emoji=emoji)]
        ])
```

Now we can rewrite the block before as:

```python
class DELETE_ITEM(CallbackButton):
    item: Item


reply_markup = DELETE_ITEM(item=item).to_keyboard()
```

Now that we have an action we would define it's `CallbackQueryHandler` using the decorator I showed before:

```python
@arbitrary_callback_query_handler(DELETE_ITEM)
async def delete_item(update: Update, context: ApplicationContext, action: DELETE_ITEM):
    ...
```
