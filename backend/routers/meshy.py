"""
Router for Meshy API high-quality 3D model generation.
Handles final production-ready 3D asset creation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from database import get_db, GalleryItem, MeshyTask, AssetType, AssetStatus
from models.gallery_item import (
    GenerateMeshyRequest, 
    MeshyTaskResponse, 
    MeshyWebhookPayload,
    FinalModelResponse,
    ErrorResponse,
)
from services.meshy_service import get_meshy_service
from services.storage_service import get_storage_service
from config import PROTOTYPES_DIR

router = APIRouter(prefix="/generate", tags=["Meshy Final Model"])


@router.post(
    "/meshy",
    response_model=MeshyTaskResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Prototype not found"},
        500: {"model": ErrorResponse, "description": "Generation failed"},
    },
    summary="Generate Final Meshy Model",
    description="Convert a Shap-E prototype into a high-quality final 3D model using Meshy API.",
)
async def generate_meshy_model(
    request: GenerateMeshyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Generate a high-quality 3D model from a prototype using Meshy API.
    
    This initiates an async task with Meshy. Use the task_id to poll
    for status or configure webhooks for completion notifications.
    
    Args:
        request: Request with prototype ID
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Task metadata for tracking the generation
    """
    try:
        meshy_service = get_meshy_service()
        storage_service = get_storage_service()
        
        # Find the source prototype
        prototype_item = db.query(GalleryItem).filter(
            GalleryItem.id == request.prototype_id,
            GalleryItem.asset_type == AssetType.PROTOTYPE,
        ).first()
        
        if not prototype_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prototype with ID {request.prototype_id} not found",
            )
        
        # Get the source 2D image for Meshy (it works better with images)
        source_image = db.query(GalleryItem).filter(
            GalleryItem.id == prototype_item.parent_id,
        ).first()
        
        if not source_image or not source_image.openai_image_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source image URL not available for Meshy generation",
            )
        
        # Create final model gallery item
        final_item = GalleryItem(
            name=f"Final - {prototype_item.name}",
            prompt=prototype_item.prompt,
            asset_type=AssetType.FINAL_MODEL,
            status=AssetStatus.PROCESSING,
            parent_id=prototype_item.id,
        )
        
        db.add(final_item)
        db.commit()
        db.refresh(final_item)
        
        # Create Meshy task
        task_response = await meshy_service.create_image_to_3d_task(
            image_url=source_image.openai_image_url,
            name=final_item.name,
        )
        
        task_id = task_response.get("result")
        
        # Store task reference
        meshy_task = MeshyTask(
            task_id=task_id,
            gallery_item_id=final_item.id,
            status="pending",
        )
        
        db.add(meshy_task)
        final_item.meshy_task_id = task_id
        db.commit()
        db.refresh(meshy_task)
        
        return MeshyTaskResponse(
            task_id=task_id,
            gallery_item_id=final_item.id,
            status="pending",
            progress=0,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Meshy task: {str(e)}",
        )


@router.get(
    "/meshy/task/{task_id}",
    response_model=MeshyTaskResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
    summary="Get Meshy Task Status",
    description="Poll the status of a Meshy generation task.",
)
async def get_meshy_task_status(
    task_id: str,
    db: Session = Depends(get_db),
):
    """
    Get the current status of a Meshy task.
    
    Args:
        task_id: The Meshy task ID
        db: Database session
        
    Returns:
        Current task status and progress
    """
    try:
        meshy_service = get_meshy_service()
        storage_service = get_storage_service()
        
        # Get local task record
        meshy_task = db.query(MeshyTask).filter(
            MeshyTask.task_id == task_id,
        ).first()
        
        if not meshy_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found",
            )
        
        # Poll Meshy API for current status
        api_status = await meshy_service.get_task_status(task_id)
        
        # Update local record
        meshy_task.status = api_status.get("status", "unknown")
        meshy_task.progress = api_status.get("progress", 0)
        
        # If completed, download files
        if meshy_task.status == "SUCCEEDED":
            gallery_item = db.query(GalleryItem).filter(
                GalleryItem.id == meshy_task.gallery_item_id,
            ).first()
            
            if gallery_item and gallery_item.status != AssetStatus.COMPLETED:
                # Download model files
                obj_path, fbx_path, texture_path = await meshy_service.download_model_files(api_status)
                
                # Update gallery item
                gallery_item.status = AssetStatus.COMPLETED
                if obj_path:
                    gallery_item.obj_path = obj_path.split("/")[-1]
                if fbx_path:
                    gallery_item.fbx_path = fbx_path.split("/")[-1]
                if texture_path:
                    gallery_item.texture_path = texture_path.split("/")[-1]
                
                meshy_task.result_url = api_status.get("model_urls", {}).get("obj")
        
        elif meshy_task.status == "FAILED":
            gallery_item = db.query(GalleryItem).filter(
                GalleryItem.id == meshy_task.gallery_item_id,
            ).first()
            
            if gallery_item:
                gallery_item.status = AssetStatus.FAILED
            
            meshy_task.error_message = api_status.get("error", "Unknown error")
        
        db.commit()
        db.refresh(meshy_task)
        
        return MeshyTaskResponse(
            task_id=meshy_task.task_id,
            gallery_item_id=meshy_task.gallery_item_id,
            status=meshy_task.status,
            progress=meshy_task.progress,
            result_url=meshy_task.result_url,
            error_message=meshy_task.error_message,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        )


@router.post(
    "/meshy/webhook",
    summary="Meshy Webhook Handler",
    description="Endpoint for receiving Meshy task completion webhooks.",
)
async def meshy_webhook(
    payload: MeshyWebhookPayload,
    db: Session = Depends(get_db),
):
    """
    Handle webhook notifications from Meshy API.
    
    This endpoint is called by Meshy when a task completes or fails.
    
    Args:
        payload: Webhook payload from Meshy
        db: Database session
        
    Returns:
        Acknowledgment response
    """
    try:
        meshy_service = get_meshy_service()
        
        # Find the task
        meshy_task = db.query(MeshyTask).filter(
            MeshyTask.task_id == payload.task_id,
        ).first()
        
        if not meshy_task:
            return {"status": "ignored", "reason": "Task not found"}
        
        # Update task status
        meshy_task.status = payload.status
        if payload.progress:
            meshy_task.progress = payload.progress
        
        # Get gallery item
        gallery_item = db.query(GalleryItem).filter(
            GalleryItem.id == meshy_task.gallery_item_id,
        ).first()
        
        if payload.status == "SUCCEEDED" and payload.result:
            # Download model files
            obj_path, fbx_path, texture_path = await meshy_service.download_model_files(payload.result)
            
            if gallery_item:
                gallery_item.status = AssetStatus.COMPLETED
                if obj_path:
                    gallery_item.obj_path = obj_path.split("/")[-1]
                if fbx_path:
                    gallery_item.fbx_path = fbx_path.split("/")[-1]
                if texture_path:
                    gallery_item.texture_path = texture_path.split("/")[-1]
            
            meshy_task.result_url = payload.result.get("model_urls", {}).get("obj")
            
        elif payload.status == "FAILED":
            if gallery_item:
                gallery_item.status = AssetStatus.FAILED
            meshy_task.error_message = payload.error
        
        db.commit()
        
        return {"status": "processed", "task_id": payload.task_id}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get(
    "/meshy/{model_id}",
    response_model=FinalModelResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Model not found"},
    },
    summary="Get Final Model Details",
    description="Get details of a completed final 3D model.",
)
async def get_final_model(
    model_id: int,
    db: Session = Depends(get_db),
):
    """
    Get details of a final 3D model.
    
    Args:
        model_id: ID of the final model
        db: Database session
        
    Returns:
        Final model metadata with download URLs
    """
    storage_service = get_storage_service()
    
    model_item = db.query(GalleryItem).filter(
        GalleryItem.id == model_id,
        GalleryItem.asset_type == AssetType.FINAL_MODEL,
    ).first()
    
    if not model_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Final model with ID {model_id} not found",
        )
    
    return FinalModelResponse(
        id=model_item.id,
        name=model_item.name,
        parent_id=model_item.parent_id,
        obj_url=storage_service.get_final_url(model_item.obj_path) if model_item.obj_path else None,
        fbx_url=storage_service.get_final_url(model_item.fbx_path) if model_item.fbx_path else None,
        texture_url=storage_service.get_final_url(model_item.texture_path) if model_item.texture_path else None,
        status=model_item.status,
        created_at=model_item.created_at,
    )


@router.get(
    "/meshy",
    summary="List All Final Models",
    description="Get a list of all final 3D models.",
)
async def list_final_models(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    List all final models with pagination.
    
    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        db: Database session
        
    Returns:
        List of final model metadata
    """
    storage_service = get_storage_service()
    
    items = db.query(GalleryItem).filter(
        GalleryItem.asset_type == AssetType.FINAL_MODEL,
    ).order_by(GalleryItem.created_at.desc()).offset(skip).limit(limit).all()
    
    total = db.query(GalleryItem).filter(
        GalleryItem.asset_type == AssetType.FINAL_MODEL,
    ).count()
    
    return {
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "parent_id": item.parent_id,
                "obj_url": storage_service.get_final_url(item.obj_path) if item.obj_path else None,
                "fbx_url": storage_service.get_final_url(item.fbx_path) if item.fbx_path else None,
                "texture_url": storage_service.get_final_url(item.texture_path) if item.texture_path else None,
                "status": item.status,
                "meshy_task_id": item.meshy_task_id,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }
