"""Database setup and models"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, Boolean, DateTime, JSON, Text
from datetime import datetime
from typing import Optional

from app.core.config import settings


# Base class for models
class Base(DeclarativeBase):
    pass


# Database models
class Request(Base):
    """Stores execution requests"""
    __tablename__ = "requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_prompt: Mapped[str] = mapped_column(Text)
    aggregated_result: Mapped[str] = mapped_column(Text)
    total_cost: Mapped[float] = mapped_column(Float)
    baseline_cost: Mapped[float] = mapped_column(Float)
    total_time: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SubTaskExecution(Base):
    """Stores individual subtask executions"""
    __tablename__ = "subtask_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String)
    subtask_id: Mapped[str] = mapped_column(String)
    task_type: Mapped[str] = mapped_column(String)
    complexity: Mapped[float] = mapped_column(Float)
    model_used: Mapped[str] = mapped_column(String)
    tokens_input: Mapped[int] = mapped_column(Integer)
    tokens_output: Mapped[int] = mapped_column(Integer)
    cost: Mapped[float] = mapped_column(Float)
    latency: Mapped[float] = mapped_column(Float)
    success: Mapped[bool] = mapped_column(Boolean)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserFeedback(Base):
    """Stores user feedback for learning"""
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    accepted: Mapped[bool] = mapped_column(Boolean)
    time_spent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LearningData(Base):
    """Stores learning patterns (shadow mode)"""
    __tablename__ = "learning_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String)
    complexity: Mapped[float] = mapped_column(Float)
    model_used: Mapped[str] = mapped_column(String)
    success: Mapped[bool] = mapped_column(Boolean)
    user_accepted: Mapped[bool] = mapped_column(Boolean)
    cost: Mapped[float] = mapped_column(Float)
    latency: Mapped[float] = mapped_column(Float)
    features: Mapped[dict] = mapped_column(JSON)  # Auto-tagged features
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# Database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Get database session"""
    async with async_session_maker() as session:
        yield session
