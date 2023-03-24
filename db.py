from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from typing import Optional


class Base(DeclarativeBase):
    pass


class CommandPermission(Base):
    __tablename__ = "cmd_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    command: Mapped[str] = mapped_column(unique=True)
    module: Mapped[str]
    allowed_for: Mapped[str]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    role: Mapped[str]
