"""
Router for gallery management endpoints.
Handles viewing, saving, and deleting gallery items.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db, GalleryItem, AssetType, AssetStatus
from models.gallery_item import (
    GalleryItemResponse,
    GalleryListResponse,
    SaveToGalleryRequest,
    DeleteGalleryItemRequest,
    SuccessResponse,
    ErrorResponse,
)
from services.storage_service import get_storage_service

router = APIRouter(prefix="/gallery", tags=["Gallery"])


@router.get(
    "",
    summary="Get All Gallery Items",
    description="Retrieve all items in the gallery with optional filtering.",
)
async def get_gallery(
    skip: int = 0,
    limit: int = 50,
    asset_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get all gallery items with pagination and filtering.
    
    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        asset_type: Filter by asset type (image_2d, prototype, final_model)
        status_filter: Filter by status (pending, processing, completed, failed)
        db: Database session
        
    Returns:
        Paginated list of gallery items
    """
    storage_service = get_storage_service()
    
    query = db.query(GalleryItem)
    
    if asset_type:
        query = query.filter(GalleryItem.asset_type == asset_type)
    
    if status_filter:
        query = query.filter(GalleryItem.status == status_filter)
    
    total = query.count()
    items = query.order_by(GalleryItem.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_urls(item):
        """Generate URLs for an item based on its type."""
        urls = {}
        
        if item.image_path:
            urls["image_url"] = storage_service.get_image_url(item.image_path)
        
        if item.gif_path:
            urls["gif_url"] = storage_service.get_prototype_url(item.gif_path)
        
        if item.obj_path:
            if item.asset_type == AssetType.PROTOTYPE:
                urls["obj_url"] = storage_service.get_prototype_url(item.obj_path)
            else:
                urls["obj_url"] = storage_service.get_final_url(item.obj_path)
        
        if item.fbx_path:
            urls["fbx_url"] = storage_service.get_final_url(item.fbx_path)
        
        if item.texture_path:
            urls["texture_url"] = storage_service.get_final_url(item.texture_path)
        
        return urls
    
    return {
        "items": [
            {
                **item.to_dict(),
                **get_urls(item),
            }
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/{item_id}",
    response_model=GalleryItemResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
    summary="Get Gallery Item",
    description="Get details of a specific gallery item.",
)
async def get_gallery_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific gallery item by ID.
    
    Args:
        item_id: ID of the item to retrieve
        db: Database session
        
    Returns:
        Gallery item details
    """
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gallery item with ID {item_id} not found",
        )
    
    return GalleryItemResponse(**item.to_dict())


@router.post(
    "/save",
    response_model=SuccessResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
    summary="Save Item to Gallery",
    description="Mark an item as saved to the gallery with an optional custom name.",
)
async def save_to_gallery(
    request: SaveToGalleryRequest,
    db: Session = Depends(get_db),
):
    """
    Save an item to the gallery.
    
    This updates the item's name if provided and marks it as a gallery item.
    
    Args:
        request: Save request with item ID and optional name
        db: Database session
        
    Returns:
        Success response
    """
    item = db.query(GalleryItem).filter(GalleryItem.id == request.item_id).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {request.item_id} not found",
        )
    
    if request.name:
        item.name = request.name
    
    db.commit()
    
    return SuccessResponse(
        success=True,
        message=f"Item {request.item_id} saved to gallery",
    )


@router.delete(
    "/{item_id}",
    response_model=SuccessResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
    summary="Delete Gallery Item",
    description="Delete a gallery item and its associated files.",
)
async def delete_gallery_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a gallery item and its files.
    
    Args:
        item_id: ID of the item to delete
        db: Database session
        
    Returns:
        Success response
    """
    storage_service = get_storage_service()
    
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gallery item with ID {item_id} not found",
        )
    
    # Delete associated files
    if item.image_path:
        storage_service.delete_file(str(storage_service.images_dir / item.image_path))
    
    if item.gif_path:
        storage_service.delete_file(str(storage_service.prototypes_dir / item.gif_path))
    
    if item.obj_path:
        if item.asset_type == AssetType.PROTOTYPE:
            storage_service.delete_file(str(storage_service.prototypes_dir / item.obj_path))
        else:
            storage_service.delete_file(str(storage_service.final_dir / item.obj_path))
    
    if item.fbx_path:
        storage_service.delete_file(str(storage_service.final_dir / item.fbx_path))
    
    if item.texture_path:
        storage_service.delete_file(str(storage_service.final_dir / item.texture_path))
    
    # Delete database record
    db.delete(item)
    db.commit()
    
    return SuccessResponse(
        success=True,
        message=f"Gallery item {item_id} deleted successfully",
    )


@router.get(
    "/prototypes/saved",
    summary="Get Saved Prototypes",
    description="Get all prototypes that have been saved to the gallery.",
)
async def get_saved_prototypes(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Get all saved prototypes.
    
    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        db: Database session
        
    Returns:
        List of saved prototypes
    """
    storage_service = get_storage_service()
    
    items = db.query(GalleryItem).filter(
        GalleryItem.asset_type == AssetType.PROTOTYPE,
        GalleryItem.status == AssetStatus.COMPLETED,
    ).order_by(GalleryItem.created_at.desc()).offset(skip).limit(limit).all()
    
    total = db.query(GalleryItem).filter(
        GalleryItem.asset_type == AssetType.PROTOTYPE,
        GalleryItem.status == AssetStatus.COMPLETED,
    ).count()
    
    return {
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "prompt": item.prompt,
                "parent_id": item.parent_id,
                "gif_url": storage_service.get_prototype_url(item.gif_path) if item.gif_path else None,
                "obj_url": storage_service.get_prototype_url(item.obj_path) if item.obj_path else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/stats",
    summary="Get Gallery Statistics",
    description="Get statistics about the gallery contents.",
)
async def get_gallery_stats(
    db: Session = Depends(get_db),
):
    """
    Get statistics about gallery contents.
    
    Args:
        db: Database session
        
    Returns:
        Gallery statistics
    """
    total_images = db.query(GalleryItem).filter(
        GalleryItem.asset_type == AssetType.IMAGE_2D,
    ).count()
    
    total_prototypes = db.query(GalleryItem).filter(
        GalleryItem.asset_type == AssetType.PROTOTYPE,
    ).count()
    
    total_finals = db.query(GalleryItem).filter(
        GalleryItem.asset_type == AssetType.FINAL_MODEL,
    ).count()
    
    completed = db.query(GalleryItem).filter(
        GalleryItem.status == AssetStatus.COMPLETED,
    ).count()
    
    processing = db.query(GalleryItem).filter(
        GalleryItem.status == AssetStatus.PROCESSING,
    ).count()
    
    failed = db.query(GalleryItem).filter(
        GalleryItem.status == AssetStatus.FAILED,
    ).count()
    
    return {
        "total_items": total_images + total_prototypes + total_finals,
        "by_type": {
            "images_2d": total_images,
            "prototypes": total_prototypes,
            "final_models": total_finals,
        },
        "by_status": {
            "completed": completed,
            "processing": processing,
            "failed": failed,
        },
    }
