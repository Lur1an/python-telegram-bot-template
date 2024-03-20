from sqlalchemy.ext.asyncio import create_async_engine
import json
import pydantic_core

def json_serializer(*args, **kwargs) -> str:
    """
    Encodes json in the same way that pydantic does.
    """
    return json.dumps(*args, default=pydantic_core.to_jsonable_python, **kwargs)

def create_engine(db_path: str):
    db_url = "sqlite+aiosqlite:///" + db_path
    return create_async_engine(url=db_url, json_serializer=json_serializer)
