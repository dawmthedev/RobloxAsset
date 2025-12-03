"""
Database module for SQLite storage of gallery items and metadata.
Uses SQLAlchemy for ORM functionality.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum

from config import DATABASE_URL

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class AssetType(str, enum.Enum):
    """Enum for different asset types in the pipeline."""
    IMAGE_2D = "image_2d"
    PROTOTYPE = "prototype"
    FINAL_MODEL = "final_model"


class AssetStatus(str, enum.Enum):
    """Enum for asset processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GalleryItem(Base):
    """
    SQLAlchemy model for gallery items.
    Stores metadata for all assets in the pipeline.
    """
    __tablename__ = "gallery_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=True)
    asset_type = Column(String(50), nullable=False)
    status = Column(String(50), default=AssetStatus.PENDING)
    
    # File paths (relative to storage directory)
    image_path = Column(String(500), nullable=True)
    gif_path = Column(String(500), nullable=True)
    obj_path = Column(String(500), nullable=True)
    fbx_path = Column(String(500), nullable=True)
    texture_path = Column(String(500), nullable=True)
    
    # Parent reference for tracking lineage
    parent_id = Column(Integer, nullable=True)
    
    # External API references
    openai_image_url = Column(String(1000), nullable=True)
    meshy_task_id = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "asset_type": self.asset_type,
            "status": self.status,
            "image_path": self.image_path,
            "gif_path": self.gif_path,
            "obj_path": self.obj_path,
            "fbx_path": self.fbx_path,
            "texture_path": self.texture_path,
            "parent_id": self.parent_id,
            "openai_image_url": self.openai_image_url,
            "meshy_task_id": self.meshy_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MeshyTask(Base):
    """
    SQLAlchemy model for tracking Meshy API tasks.
    Used for async task polling and webhook handling.
    """
    __tablename__ = "meshy_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, nullable=False, index=True)
    gallery_item_id = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")
    progress = Column(Integer, default=0)
    result_url = Column(String(1000), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "gallery_item_id": self.gallery_item_id,
            "status": self.status,
            "progress": self.progress,
            "result_url": self.result_url,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency function for FastAPI to get database session.
    Yields a session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
