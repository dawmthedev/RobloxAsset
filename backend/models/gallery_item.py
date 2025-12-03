"""
Pydantic models for API request/response validation.
These models define the schema for data transfer between frontend and backend.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AssetType(str, Enum):
    """Asset type enumeration."""
    IMAGE_2D = "image_2d"
    PROTOTYPE = "prototype"
    FINAL_MODEL = "final_model"


class AssetStatus(str, Enum):
    """Asset processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================
# 2D Image Generation Models
# ============================================

class Generate2DRequest(BaseModel):
    """Request model for 2D image generation."""
    prompt: str = Field(..., min_length=1, max_length=1000, description="Text prompt for image generation")
    refinement_notes: Optional[str] = Field(None, max_length=500, description="Optional refinement notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "A sleek futuristic sword with glowing blue edges",
                "refinement_notes": "Make it more metallic"
            }
        }


class Refine2DRequest(BaseModel):
    """Request model for 2D image refinement."""
    image_id: int = Field(..., description="ID of the original image to refine")
    refinement_text: str = Field(..., min_length=1, max_length=500, description="Refinement instructions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "image_id": 1,
                "refinement_text": "Add more detail to the handle and make the blade sharper"
            }
        }


class Image2DResponse(BaseModel):
    """Response model for 2D image operations."""
    id: int
    name: str
    prompt: str
    image_url: str
    image_path: str
    status: str
    created_at: datetime


# ============================================
# Shap-E Prototype Models
# ============================================

class GenerateShapERequest(BaseModel):
    """Request model for Shap-E prototype generation."""
    image_id: int = Field(..., description="ID of the 2D image to convert to 3D")
    
    class Config:
        json_schema_extra = {
            "example": {
                "image_id": 1
            }
        }


class ShapEResponse(BaseModel):
    """Response model for Shap-E prototype generation."""
    id: int
    name: str
    parent_id: int
    gif_url: str
    obj_url: str
    status: str
    created_at: datetime


# ============================================
# Meshy Final Model Models
# ============================================

class GenerateMeshyRequest(BaseModel):
    """Request model for Meshy final model generation."""
    prototype_id: int = Field(..., description="ID of the prototype to convert to final model")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prototype_id": 1
            }
        }


class MeshyTaskResponse(BaseModel):
    """Response model for Meshy task status."""
    task_id: str
    gallery_item_id: int
    status: str
    progress: int
    result_url: Optional[str] = None
    error_message: Optional[str] = None


class MeshyWebhookPayload(BaseModel):
    """Webhook payload from Meshy API."""
    task_id: str
    status: str
    progress: Optional[int] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class FinalModelResponse(BaseModel):
    """Response model for completed final model."""
    id: int
    name: str
    parent_id: int
    obj_url: Optional[str] = None
    fbx_url: Optional[str] = None
    texture_url: Optional[str] = None
    status: str
    created_at: datetime


# ============================================
# Gallery Models
# ============================================

class GalleryItemResponse(BaseModel):
    """Response model for gallery items."""
    id: int
    name: str
    prompt: Optional[str] = None
    asset_type: str
    status: str
    image_path: Optional[str] = None
    gif_path: Optional[str] = None
    obj_path: Optional[str] = None
    fbx_path: Optional[str] = None
    texture_path: Optional[str] = None
    parent_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GalleryListResponse(BaseModel):
    """Response model for gallery list."""
    items: List[GalleryItemResponse]
    total: int


class SaveToGalleryRequest(BaseModel):
    """Request model for saving item to gallery."""
    item_id: int = Field(..., description="ID of the item to save to gallery")
    name: Optional[str] = Field(None, max_length=255, description="Optional custom name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "item_id": 1,
                "name": "My Awesome Sword Prototype"
            }
        }


class DeleteGalleryItemRequest(BaseModel):
    """Request model for deleting gallery item."""
    item_id: int = Field(..., description="ID of the item to delete")


# ============================================
# Generic Response Models
# ============================================

class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None
