"""
Router for 2D image generation endpoints.
Handles creation of 2D concept images using procedural CPU-only rendering.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db, GalleryItem, AssetType, AssetStatus
from models.gallery_item import Generate2DRequest, Image2DResponse, ErrorResponse
from services.procedural_2d_service import get_procedural_2d_service
from services.huggingface_2d_service import get_huggingface_2d_service
from services.storage_service import get_storage_service
import os

router = APIRouter(prefix="/generate", tags=["2D Generation"])


@router.post(
    "/2d",
    response_model=Image2DResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Generation failed"},
    },
    summary="Generate 2D Concept Image",
    description="Generate a clean 2D concept image using procedural CPU-only rendering. "
                "The image will be a centered object with shape/color based on prompt heuristics.",
)
async def generate_2d_image(
    request: Generate2DRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a 2D concept image from a text prompt using procedural methods.
    
    The generated image will be:
    - A centered object silhouette
    - On transparent background
    - Shape determined by prompt keywords (sword, crate, orb, etc.)
    - Color extracted from prompt words
    - CPU-only rendering, no GPU required
    
    Args:
        request: Generation request with prompt and optional refinement notes
        db: Database session
        
    Returns:
        Generated image metadata including URL and file path
    """
    try:
        # Prefer Hugging Face when available, but fall back gracefully on any error
        hf_service = get_huggingface_2d_service()
        procedural_service = get_procedural_2d_service()

        if hf_service.is_available():
            try:
                # Primary path: Hugging Face AI image generation
                local_path, image_url, filename = await hf_service.generate_2d_image(
                    prompt=request.prompt,
                    refinement_notes=request.refinement_notes,
                )
            except Exception:
                # If HF is down / 503 / rate limited, fall back to procedural
                local_path, image_url, filename = await procedural_service.generate_2d_image(
                    prompt=request.prompt,
                    refinement_notes=request.refinement_notes,
                )
        else:
            # No HF key configured: always use procedural
            local_path, image_url, filename = await procedural_service.generate_2d_image(
                prompt=request.prompt,
                refinement_notes=request.refinement_notes,
            )
        
        # Create gallery item for tracking
        gallery_item = GalleryItem(
            name=f"2D Concept - {request.prompt[:50]}...",
            prompt=request.prompt,
            asset_type=AssetType.IMAGE_2D,
            status=AssetStatus.COMPLETED,
            image_path=filename,
        )
        
        db.add(gallery_item)
        db.commit()
        db.refresh(gallery_item)
        
        return Image2DResponse(
            id=gallery_item.id,
            name=gallery_item.name,
            prompt=request.prompt,
            image_url=image_url,
            image_path=filename,
            status=gallery_item.status,
            created_at=gallery_item.created_at,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        # Avoid bubbling up huge HTML responses; return a short, clean error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate image. Please try again in a moment.",
        )


@router.get(
    "/2d/{image_id}",
    response_model=Image2DResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Image not found"},
    },
    summary="Get 2D Image Details",
    description="Retrieve details of a previously generated 2D image.",
)
async def get_2d_image(
    image_id: int,
    db: Session = Depends(get_db),
):
    """
    Get details of a specific 2D image by ID.
    
    Args:
        image_id: ID of the image to retrieve
        db: Database session
        
    Returns:
        Image metadata
    """
    storage_service = get_storage_service()
    
    gallery_item = db.query(GalleryItem).filter(
        GalleryItem.id == image_id,
        GalleryItem.asset_type == AssetType.IMAGE_2D,
    ).first()
    
    if not gallery_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID {image_id} not found",
        )
    
    image_url = storage_service.get_image_url(gallery_item.image_path)
    
    return Image2DResponse(
        id=gallery_item.id,
        name=gallery_item.name,
        prompt=gallery_item.prompt,
        image_url=image_url,
        image_path=gallery_item.image_path,
        status=gallery_item.status,
        created_at=gallery_item.created_at,
    )


@router.get(
    "/2d",
    summary="List All 2D Images",
    description="Get a list of all generated 2D concept images.",
)
async def list_2d_images(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    List all generated 2D images with pagination.
    
    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        db: Database session
        
    Returns:
        List of image metadata
    """
    storage_service = get_storage_service()
    
    items = db.query(GalleryItem).filter(
        GalleryItem.asset_type == AssetType.IMAGE_2D,
    ).order_by(GalleryItem.created_at.desc()).offset(skip).limit(limit).all()
    
    total = db.query(GalleryItem).filter(
        GalleryItem.asset_type == AssetType.IMAGE_2D,
    ).count()
    
    return {
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "prompt": item.prompt,
                "image_url": storage_service.get_image_url(item.image_path) if item.image_path else None,
                "image_path": item.image_path,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }
