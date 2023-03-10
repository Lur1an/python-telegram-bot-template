from sqlalchemy.orm import mapped_column, Mapped

from src.db.config import Base


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    telegram_username: Mapped[str] = mapped_column(nullable=False)
