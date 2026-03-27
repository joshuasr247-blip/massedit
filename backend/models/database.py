"""
SQLAlchemy models and async database setup for MassEdit.
Uses SQLite with aiosqlite for async operations.
"""

import logging
from datetime import datetime
from typing import Optional, AsyncGenerator

from sqlalchemy import Column, String, DateTime, Integer, Float, Text, JSON, ForeignKey, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, relationship

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================================================
# Database Models
# ============================================================================

class ProjectDB(Base):
    """Project database model."""
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    prompt = Column(Text, nullable=True)

    # JSON columns for complex structures
    boxes = Column(JSON, nullable=False, default=[])
    edit_plan = Column(JSON, nullable=True)
    matrix = Column(JSON, nullable=False, default={})

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    render_jobs = relationship("RenderJobDB", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProjectDB {self.id}: {self.name}>"


class RenderJobDB(Base):
    """Render job database model."""
    __tablename__ = "render_jobs"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    output_index = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="queued")
    progress = Column(Integer, nullable=False, default=0)
    output_path = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # JSON mapping of box_id -> clip_id
    clip_assignments = Column(JSON, nullable=False, default={})

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    project = relationship("ProjectDB", back_populates="render_jobs")

    def __repr__(self):
        return f"<RenderJobDB {self.id}: {self.status}>"


# ============================================================================
# Async Database Setup
# ============================================================================

class Database:
    """Async database manager for MassEdit."""

    def __init__(self, database_url: str):
        """
        Initialize database.

        Args:
            database_url: SQLAlchemy async database URL (e.g., sqlite+aiosqlite:///./db.sqlite3)
        """
        self.database_url = database_url
        self.engine = None
        self.async_session_maker = None

    async def init_db(self):
        """Initialize database connection and create tables."""
        logger.info(f"Initializing database: {self.database_url}")

        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )

        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        FastAPI dependency to get async database session.

        Yields:
            AsyncSession: Database session
        """
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized. Call init_db() first.")

        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()


# ============================================================================
# Global Database Instance
# ============================================================================

_db_instance: Optional[Database] = None


def get_database(database_url: str = None) -> Database:
    """
    Get or create the global database instance.

    Args:
        database_url: Database URL (optional, uses default if not provided)

    Returns:
        Database: The global database instance
    """
    global _db_instance

    if _db_instance is None:
        if not database_url:
            import os
            storage = os.getenv("MASSEDIT_STORAGE_PATH", "/tmp/massedit-storage")
            os.makedirs(storage, exist_ok=True)
            database_url = f"sqlite+aiosqlite:///{storage}/massedit.db"
        _db_instance = Database(database_url)

    return _db_instance


def reset_database():
    """Reset the global database instance (for testing)."""
    global _db_instance
    _db_instance = None
