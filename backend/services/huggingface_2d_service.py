"""
Hugging Face 2D Image Generation Service.
Uses Hugging Face's free Inference API to generate actual images from text prompts.
Generates recognizable objects (cats, cars, houses, etc.) not just shapes.
"""

import os
import uuid
import httpx
from datetime import datetime
from typing import Tuple, Optional
from pathlib import Path

from config import IMAGES_DIR

# Hugging Face API configuration - using new router endpoint
HF_API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")


class HuggingFace2DService:
    """
    Service for generating 2D images using Hugging Face's Inference API.
    Generates actual recognizable objects from text prompts.
    """

    def __init__(self):
        """Initialize the Hugging Face 2D service."""
        self.api_url = HF_API_URL
        self.headers = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}
        
    def _build_prompt(self, user_prompt: str, refinement_notes: Optional[str] = None) -> str:
        """
        Build an optimized prompt for 3D asset reference generation.
        
        Args:
            user_prompt: User's description
            refinement_notes: Optional refinement instructions
            
        Returns:
            Optimized prompt string
        """
        # Enhance prompt for clean, centered object renders
        base_prompt = f"""A clean 3D render of {user_prompt}, centered in frame, 
plain white background, studio lighting, high quality, 
single isolated object, product photography style, 
no text, no watermarks, professional render, 
game asset style, Roblox style"""

        if refinement_notes:
            base_prompt += f", {refinement_notes}"
            
        return base_prompt

    async def generate_2d_image(
        self, 
        prompt: str, 
        refinement_notes: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Generate a 2D image using Hugging Face's Inference API.
        
        Args:
            prompt: Text description of the desired object
            refinement_notes: Optional refinement instructions
            
        Returns:
            Tuple of (local_file_path, image_url, filename)
        """
        # Build optimized prompt
        full_prompt = self._build_prompt(prompt, refinement_notes)
        
        # Call Hugging Face API
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.api_url,
                headers=self.headers,
                json={
                    "inputs": full_prompt,
                    "parameters": {
                        "negative_prompt": "blurry, bad quality, distorted, multiple objects, busy background, text, watermark, logo",
                        "num_inference_steps": 25,
                        "guidance_scale": 7.5,
                        "width": 512,
                        "height": 512,
                    }
                }
            )
            
            if response.status_code != 200:
                error_msg = response.text
                raise Exception(f"Hugging Face API error: {response.status_code} - {error_msg}")
            
            image_bytes = response.content
        
        # Save to file (HF returns JPEG)
        filename = f"hf_{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        local_path = IMAGES_DIR / filename
        
        with open(local_path, "wb") as f:
            f.write(image_bytes)
        
        return str(local_path), f"/storage/images/{filename}", filename
    
    def is_available(self) -> bool:
        """Check if the service is available (API key configured)."""
        return bool(HF_API_KEY)


# Singleton instance
_hf_service: Optional[HuggingFace2DService] = None


def get_huggingface_2d_service() -> HuggingFace2DService:
    """
    Get or create the Hugging Face 2D service singleton.
    
    Returns:
        HuggingFace2DService instance
    """
    global _hf_service
    if _hf_service is None:
        _hf_service = HuggingFace2DService()
    return _hf_service
