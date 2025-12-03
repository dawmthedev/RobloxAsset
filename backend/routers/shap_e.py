"""
Router for Shap-E 3D prototype generation endpoints.
Handles conversion of 2D images to 3D prototypes.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db, GalleryItem, AssetType, AssetStatus
from models.gallery_item import GenerateShapERequest, ShapEResponse, ErrorResponse
from services.shap_e_service import get_shap_e_service
from services.storage_service import get_storage_service
from config import IMAGES_DIR

router = APIRouter(prefix="/generate", tags=["Shap-E Prototype"])


async def _generate_prototype_task(
    image_id: int,
    image_path: str,
    db_session_factory,
):
    """
    Background task for generating Shap-E prototype.
    
    Args:
        image_id: ID of the source 2D image
        image_path: Path to the source image file
        db_session_factory: Factory for creating database sessions
    """
    db = db_session_factory()
    try:
        shap_e_service = get_shap_e_service()
        
        # Generate the prototype
        obj_path, gif_path, obj_filename, gif_filename = await shap_e_service.generate_prototype(
            image_path=image_path,
        )
        
        # Update the gallery item
        prototype_item = db.query(GalleryItem).filter(
            GalleryItem.parent_id == image_id,
            GalleryItem.asset_type == AssetType.PROTOTYPE,
            GalleryItem.status == AssetStatus.PROCESSING,
        ).first()
        
        if prototype_item:
            prototype_item.status = AssetStatus.COMPLETED
            prototype_item.obj_path = obj_filename
            prototype_item.gif_path = gif_filename
            db.commit()
            
    except Exception as e:
        # Mark as failed
        prototype_item = db.query(GalleryItem).filter(
            GalleryItem.parent_id == image_id,
            GalleryItem.asset_type == AssetType.PROTOTYPE,
            GalleryItem.status == AssetStatus.PROCESSING,
        ).first()
        
        if prototype_item:
            prototype_item.status = AssetStatus.FAILED
            db.commit()
        
        print(f"Prototype generation failed: {e}")
    finally:
        db.close()


@router.post(
    "/shap_e",
    response_model=ShapEResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Source image not found"},
        500: {"model": ErrorResponse, "description": "Generation failed"},
        503: {"model": ErrorResponse, "description": "Shap-E not available"},
    },
    summary="Generate Shap-E Prototype",
    description="Convert a 2D image into a 3D prototype using Shap-E.",
)
async def generate_shap_e_prototype(
    request: GenerateShapERequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Generate a 3D prototype from a 2D image using Shap-E.
    
    This creates:
    - An OBJ/PLY mesh file
    - A turntable GIF preview
    
    The generation runs in the background. Poll the status endpoint
    to check for completion.
    
    Args:
        request: Request with source image ID
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Prototype metadata (status will be 'processing' initially)
    """
    try:
        # Check if Shap-E is available
        shap_e_service = get_shap_e_service()
        if not shap_e_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Shap-E is not installed. Please install it with: pip install shap-e",
            )
        
        storage_service = get_storage_service()
        
        # Find the source 2D image
        source_item = db.query(GalleryItem).filter(
            GalleryItem.id == request.image_id,
            GalleryItem.asset_type == AssetType.IMAGE_2D,
        ).first()
        
        if not source_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source image with ID {request.image_id} not found",
            )
        
        # Create prototype gallery item (processing status)
        prototype_item = GalleryItem(
            name=f"Prototype - {source_item.name}",
            prompt=source_item.prompt,
            asset_type=AssetType.PROTOTYPE,
            status=AssetStatus.PROCESSING,
            parent_id=source_item.id,
        )
        
        db.add(prototype_item)
        db.commit()
        db.refresh(prototype_item)
        
        # Get the full image path
        image_path = str(IMAGES_DIR / source_item.image_path)
        
        # For synchronous generation (simpler approach)
        # In production, use background tasks for long-running operations
        try:
            obj_path, gif_path, obj_filename, gif_filename = await shap_e_service.generate_prototype(
                image_path=image_path,
            )
            
            # Update with results
            prototype_item.status = AssetStatus.COMPLETED
            prototype_item.obj_path = obj_filename
            prototype_item.gif_path = gif_filename
            db.commit()
            db.refresh(prototype_item)
            
        except Exception as e:
            prototype_item.status = AssetStatus.FAILED
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Prototype generation failed: {str(e)}",
            )
        
        # Generate URLs
        gif_url = storage_service.get_prototype_url(prototype_item.gif_path) if prototype_item.gif_path else ""
        obj_url = storage_service.get_prototype_url(prototype_item.obj_path) if prototype_item.obj_path else ""
        
        return ShapEResponse(
            id=prototype_item.id,
            name=prototype_item.name,
            parent_id=prototype_item.parent_id,
            gif_url=gif_url,
            obj_url=obj_url,
            status=prototype_item.status,
            created_at=prototype_item.created_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate prototype: {str(e)}",
        )


@router.get(
    "/shap_e/{prototype_id}",
    response_model=ShapEResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Prototype not found"},
    },
    summary="Get Prototype Status",
    description="Get the status and details of a Shap-E prototype.",
)
async def get_prototype_status(
    prototype_id: int,
    db: Session = Depends(get_db),
):
    """
    Get the current status of a prototype generation.
    
    Args:
        prototype_id: ID of the prototype
        db: Database session
        
    Returns:
        Prototype metadata with current status
    """
    storage_service = get_storage_service()
    
    prototype_item = db.query(GalleryItem).filter(
        GalleryItem.id == prototype_id,
        GalleryItem.asset_type == AssetType.PROTOTYPE,
    ).first()
    
    if not prototype_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prototype with ID {prototype_id} not found",
        )
    
    gif_url = storage_service.get_prototype_url(prototype_item.gif_path) if prototype_item.gif_path else ""
    obj_url = storage_service.get_prototype_url(prototype_item.obj_path) if prototype_item.obj_path else ""
    
    return ShapEResponse(
        id=prototype_item.id,
        name=prototype_item.name,
        parent_id=prototype_item.parent_id,
        gif_url=gif_url,
        obj_url=obj_url,
        status=prototype_item.status,
        created_at=prototype_item.created_at,
    )


@router.get(
    "/shap_e",
    summary="List All Prototypes",
    description="Get a list of all generated Shap-E prototypes.",
)
async def list_prototypes(
    skip: int = 0,
    limit: int = 50,
    status_filter: str = None,
    db: Session = Depends(get_db),
):
    """
    List all prototypes with optional filtering.
    
    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        status_filter: Optional status filter (processing, completed, failed)
        db: Database session
        
    Returns:
        List of prototype metadata
    """
    storage_service = get_storage_service()
    
    query = db.query(GalleryItem).filter(
        GalleryItem.asset_type == AssetType.PROTOTYPE,
    )
    
    if status_filter:
        query = query.filter(GalleryItem.status == status_filter)
    
    items = query.order_by(GalleryItem.created_at.desc()).offset(skip).limit(limit).all()
    total = query.count()
    
    return {
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "parent_id": item.parent_id,
                "gif_url": storage_service.get_prototype_url(item.gif_path) if item.gif_path else None,
                "obj_url": storage_service.get_prototype_url(item.obj_path) if item.obj_path else None,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }
