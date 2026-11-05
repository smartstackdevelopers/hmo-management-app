"""SQLAlchemy declarative base shared by all domain models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Metadata root for Alembic and model discovery."""
