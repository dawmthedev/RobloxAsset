"""
Router for 2D image refinement endpoints.
Handles iterative refinement of 2D concept images.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db, GalleryItem, AssetType, AssetStatus
from models.gallery_item import Refine2DRequest, Image2DResponse, ErrorResponse
from services.huggingface_2d_service import get_huggingface_2d_service
from services.procedural_2d_service import get_procedural_2d_service
from services.storage_service import get_storage_service

router = APIRouter(prefix="/refine", tags=["2D Refinement"])


@router.post(
    "/2d",
    response_model=Image2DResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Original image not found"},
        500: {"model": ErrorResponse, "description": "Refinement failed"},
    },
    summary="Refine 2D Image",
    description="Create a refined version of an existing 2D image based on feedback.",
)
async def refine_2d_image(
    request: Refine2DRequest,
    db: Session = Depends(get_db),
):
    """
    Refine an existing 2D image based on user feedback.
    
    This creates a new image that incorporates the refinement instructions
    while maintaining the essence of the original design.
    
    Args:
        request: Refinement request with original image ID and refinement text
        db: Database session
        
    Returns:
        New refined image metadata
    """
    try:
        # Get services
        hf_service = get_huggingface_2d_service()
        procedural_service = get_procedural_2d_service()
        storage_service = get_storage_service()
        
        # Find the original image
        original_item = db.query(GalleryItem).filter(
            GalleryItem.id == request.image_id,
            GalleryItem.asset_type == AssetType.IMAGE_2D,
        ).first()
        
        if not original_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Original image with ID {request.image_id} not found",
            )
        
        # Decide which generator to use
        if hf_service.is_available():
            # Use Hugging Face: combine original prompt + refinement notes
            combined_prompt = original_item.prompt
            refinement_notes = request.refinement_text or None
            local_path, image_url_from_service, filename = await hf_service.generate_2d_image(
                prompt=combined_prompt,
                refinement_notes=refinement_notes,
            )
        else:
            # Fallback: procedural refinement using combined prompt
            combined_prompt = f"{original_item.prompt}. {request.refinement_text}"
            local_path, image_url_from_service, filename = await procedural_service.generate_2d_image(
                prompt=combined_prompt,
                refinement_notes=None,
            )
        
        # Create new gallery item for the refined image
        refined_item = GalleryItem(
            name=f"Refined - {original_item.name}",
            prompt=f"{original_item.prompt}\n\nRefinement: {request.refinement_text}",
            asset_type=AssetType.IMAGE_2D,
            status=AssetStatus.COMPLETED,
            image_path=filename,
            parent_id=original_item.id,  # Track lineage
        )
        
        db.add(refined_item)
        db.commit()
        db.refresh(refined_item)
        
        # Generate accessible URL
        image_url = storage_service.get_image_url(filename)
        
        return Image2DResponse(
            id=refined_item.id,
            name=refined_item.name,
            prompt=refined_item.prompt,
            image_url=image_url,
            image_path=filename,
            status=refined_item.status,
            created_at=refined_item.created_at,
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refine image: {str(e)}",
        )


@router.get(
    "/2d/{image_id}/history",
    summary="Get Refinement History",
    description="Get the refinement history for an image, showing all versions.",
)
async def get_refinement_history(
    image_id: int,
    db: Session = Depends(get_db),
):
    """
    Get the complete refinement history for an image.
    
    This traces back through parent_id references to show all
    versions of an image from original to latest refinement.
    
    Args:
        image_id: ID of any image in the refinement chain
        db: Database session
        
    Returns:
        List of all images in the refinement chain
    """
    storage_service = get_storage_service()
    
    # Find the starting image
    current_item = db.query(GalleryItem).filter(
        GalleryItem.id == image_id,
    ).first()
    
    if not current_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID {image_id} not found",
        )
    
    # Trace back to the original
    history = []
    visited = set()
    
    # First, go back to find the root
    root_item = current_item
    while root_item.parent_id and root_item.parent_id not in visited:
        visited.add(root_item.id)
        parent = db.query(GalleryItem).filter(
            GalleryItem.id == root_item.parent_id,
        ).first()
        if parent:
            root_item = parent
        else:
            break
    
    # Now collect all descendants from the root
    def collect_chain(item):
        result = [{
            "id": item.id,
            "name": item.name,
            "prompt": item.prompt,
            "image_url": storage_service.get_image_url(item.image_path) if item.image_path else None,
            "parent_id": item.parent_id,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }]
        
        # Find children
        children = db.query(GalleryItem).filter(
            GalleryItem.parent_id == item.id,
        ).order_by(GalleryItem.created_at).all()
        
        for child in children:
            result.extend(collect_chain(child))
        
        return result
    
    history = collect_chain(root_item)
    
    return {
        "root_id": root_item.id,
        "current_id": image_id,
        "history": history,
        "total_versions": len(history),
    }


@router.post(
    "/2d/batch",
    summary="Generate Multiple Refinement Variants",
    description="Generate multiple refined variants of an image at once.",
)
async def batch_refine_2d(
    image_id: int,
    refinement_texts: list[str],
    db: Session = Depends(get_db),
):
    """
    Generate multiple refinement variants of an image.
    
    Useful for exploring different directions for refinement.
    
    Args:
        image_id: ID of the original image
        refinement_texts: List of different refinement instructions
        db: Database session
        
    Returns:
        List of refined image metadata
    """
    if len(refinement_texts) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 variants can be generated at once",
        )
    
    results = []
    errors = []
    
    for refinement_text in refinement_texts:
        try:
            request = Refine2DRequest(
                image_id=image_id,
                refinement_text=refinement_text,
            )
            result = await refine_2d_image(request, db)
            results.append(result)
        except Exception as e:
            errors.append({
                "refinement_text": refinement_text,
                "error": str(e),
            })
    
    return {
        "successful": results,
        "failed": errors,
        "total_requested": len(refinement_texts),
        "total_successful": len(results),
    }
