from enum import Enum
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column
import sqlalchemy as sa


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class PydanticType(sa.types.TypeDecorator):
    impl = sa.types.JSON

    def __init__(self, pydantic_type):
        super().__init__()
        self.pydantic_type = pydantic_type

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(sa.JSON())

    def process_bind_param(self, value, dialect):
        return value.model_dump() if value else None

    def process_result_value(self, value, dialect):
        return self.pydantic_type.model_validate(value) if value else None


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False, index=True)
    is_bot: Mapped[bool] = mapped_column(nullable=False)
    full_name: Mapped[str] = mapped_column(nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(nullable=True)
    """
    Can be hidden due to privacy settings
    """
    role: Mapped[UserRole] = mapped_column(nullable=False, default=UserRole.USER)
    admin: Mapped[bool] = mapped_column(nullable=False, default=False)
