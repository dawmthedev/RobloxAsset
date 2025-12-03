"""
Meshy Service for high-quality 3D model generation.
Uses Meshy API for final production-ready 3D assets.
"""

import os
import uuid
import httpx
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

from config import MESHY_API_KEY, MESHY_API_BASE_URL, MESHY_WEBHOOK_URL, FINAL_DIR


class MeshyService:
    """
    Service class for Meshy API integration.
    Handles high-quality 3D model generation with async task polling.
    """

    def __init__(self):
        """Initialize Meshy API client."""
        if not MESHY_API_KEY:
            raise ValueError("MESHY_API_KEY environment variable is not set")
        
        self.api_key = MESHY_API_KEY
        self.base_url = MESHY_API_BASE_URL
        self.webhook_url = MESHY_WEBHOOK_URL
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_image_to_3d_task(
        self,
        image_url: str,
        name: Optional[str] = None,
        art_style: str = "realistic",
        negative_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an image-to-3D generation task using Meshy API.
        
        Args:
            image_url: URL of the source image
            name: Optional name for the task
            art_style: Art style for the model (realistic, cartoon, etc.)
            negative_prompt: Things to avoid in the generation
            
        Returns:
            Task creation response with task_id
        """
        endpoint = f"{self.base_url}/image-to-3d"
        
        payload = {
            "image_url": image_url,
            "enable_pbr": True,  # Enable PBR materials
            "art_style": art_style,
        }
        
        if name:
            payload["name"] = name
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        if self.webhook_url:
            payload["webhook_url"] = self.webhook_url
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def create_text_to_3d_task(
        self,
        prompt: str,
        name: Optional[str] = None,
        art_style: str = "realistic",
        negative_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a text-to-3D generation task using Meshy API.
        
        Args:
            prompt: Text description of the desired 3D model
            name: Optional name for the task
            art_style: Art style for the model
            negative_prompt: Things to avoid in the generation
            
        Returns:
            Task creation response with task_id
        """
        endpoint = f"{self.base_url}/text-to-3d"
        
        payload = {
            "prompt": prompt,
            "enable_pbr": True,
            "art_style": art_style,
            "mode": "preview",  # Start with preview, then refine
        }
        
        if name:
            payload["name"] = name
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        if self.webhook_url:
            payload["webhook_url"] = self.webhook_url
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a Meshy task.
        
        Args:
            task_id: The Meshy task ID
            
        Returns:
            Task status response
        """
        endpoint = f"{self.base_url}/image-to-3d/{task_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def poll_task_until_complete(
        self,
        task_id: str,
        poll_interval: float = 5.0,
        max_attempts: int = 120,  # 10 minutes max
    ) -> Dict[str, Any]:
        """
        Poll a task until it completes or fails.
        
        Args:
            task_id: The Meshy task ID
            poll_interval: Seconds between poll attempts
            max_attempts: Maximum number of poll attempts
            
        Returns:
            Final task status
        """
        for attempt in range(max_attempts):
            status = await self.get_task_status(task_id)
            
            task_status = status.get("status", "").lower()
            
            if task_status == "succeeded":
                return status
            elif task_status in ["failed", "expired"]:
                raise Exception(f"Task {task_id} failed: {status.get('error', 'Unknown error')}")
            
            # Still processing, wait and retry
            await asyncio.sleep(poll_interval)
        
        raise TimeoutError(f"Task {task_id} did not complete within the timeout period")

    async def download_model_files(
        self,
        task_result: Dict[str, Any],
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Download the generated model files from Meshy.
        
        Args:
            task_result: The completed task result containing model URLs
            
        Returns:
            Tuple of (obj_path, fbx_path, texture_path)
        """
        base_name = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        obj_path = None
        fbx_path = None
        texture_path = None
        
        async with httpx.AsyncClient() as client:
            # Download OBJ file
            obj_url = task_result.get("model_urls", {}).get("obj")
            if obj_url:
                obj_filename = f"{base_name}.obj"
                obj_path = FINAL_DIR / obj_filename
                response = await client.get(obj_url, timeout=60.0)
                response.raise_for_status()
                with open(obj_path, "wb") as f:
                    f.write(response.content)
                obj_path = str(obj_path)
            
            # Download FBX file
            fbx_url = task_result.get("model_urls", {}).get("fbx")
            if fbx_url:
                fbx_filename = f"{base_name}.fbx"
                fbx_path = FINAL_DIR / fbx_filename
                response = await client.get(fbx_url, timeout=60.0)
                response.raise_for_status()
                with open(fbx_path, "wb") as f:
                    f.write(response.content)
                fbx_path = str(fbx_path)
            
            # Download texture files
            texture_urls = task_result.get("texture_urls", [])
            if texture_urls:
                # Download the first/main texture
                texture_url = texture_urls[0] if isinstance(texture_urls, list) else texture_urls.get("base_color")
                if texture_url:
                    texture_filename = f"{base_name}_texture.png"
                    texture_path = FINAL_DIR / texture_filename
                    response = await client.get(texture_url, timeout=60.0)
                    response.raise_for_status()
                    with open(texture_path, "wb") as f:
                        f.write(response.content)
                    texture_path = str(texture_path)
        
        return obj_path, fbx_path, texture_path

    async def generate_final_model(
        self,
        image_url: str,
        name: Optional[str] = None,
    ) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        """
        Complete workflow: create task, poll until complete, download files.
        
        Args:
            image_url: URL of the source image
            name: Optional name for the model
            
        Returns:
            Tuple of (task_id, obj_path, fbx_path, texture_path)
        """
        # Create the task
        task_response = await self.create_image_to_3d_task(
            image_url=image_url,
            name=name,
        )
        
        task_id = task_response.get("result")
        
        # Poll until complete
        result = await self.poll_task_until_complete(task_id)
        
        # Download the files
        obj_path, fbx_path, texture_path = await self.download_model_files(result)
        
        return task_id, obj_path, fbx_path, texture_path

    def validate_api_key(self) -> bool:
        """
        Validate that the Meshy API key is working.
        
        Returns:
            True if API key is valid, False otherwise
        """
        try:
            import httpx
            response = httpx.get(
                f"{self.base_url}/image-to-3d",
                headers=self.headers,
                timeout=10.0,
            )
            # 401 means unauthorized, anything else means the key format is valid
            return response.status_code != 401
        except Exception:
            return False


# Singleton instance
_meshy_service: Optional[MeshyService] = None


def get_meshy_service() -> MeshyService:
    """
    Get or create the Meshy service singleton.
    
    Returns:
        MeshyService instance
    """
    global _meshy_service
    if _meshy_service is None:
        _meshy_service = MeshyService()
    return _meshy_service
