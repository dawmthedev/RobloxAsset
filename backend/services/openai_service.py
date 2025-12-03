"""
OpenAI Service for 2D image generation and refinement.
Uses DALL-E 3 API for generating clean product renders.
"""

import os
import uuid
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

from openai import OpenAI

from config import (
    OPENAI_API_KEY,
    OPENAI_IMAGE_MODEL,
    OPENAI_IMAGE_SIZE,
    OPENAI_IMAGE_QUALITY,
    IMAGES_DIR,
)


class OpenAIService:
    """
    Service class for OpenAI image generation operations.
    Handles 2D concept generation and refinement using DALL-E.
    """

    def __init__(self):
        """Initialize OpenAI client with API key."""
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def _build_product_prompt(self, user_prompt: str, refinement_notes: Optional[str] = None) -> str:
        """
        Build a structured prompt that ensures clean product renders.
        Forces the model to output centered objects on plain backgrounds.
        
        Args:
            user_prompt: The user's description of the desired object
            refinement_notes: Optional additional refinement instructions
            
        Returns:
            Formatted prompt string optimized for product renders
        """
        base_prompt = f"""Create a professional product render of: {user_prompt}

STRICT REQUIREMENTS:
- Clean, plain white or light gray background
- Object must be perfectly centered in frame
- No environment, scene, or background elements
- Studio lighting with soft shadows
- High detail product photography style
- Single isolated object only
- No text, watermarks, or labels
- Professional 3D render quality
- Object should fill 70-80% of the frame"""

        if refinement_notes:
            base_prompt += f"\n\nADDITIONAL REFINEMENTS:\n{refinement_notes}"

        return base_prompt

    async def generate_2d_image(
        self, 
        prompt: str, 
        refinement_notes: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Generate a 2D concept image using DALL-E.
        
        Args:
            prompt: Text description of the desired object
            refinement_notes: Optional refinement instructions
            
        Returns:
            Tuple of (local_file_path, openai_url, filename)
        """
        # Build optimized prompt for product renders
        full_prompt = self._build_product_prompt(prompt, refinement_notes)
        
        # Generate image using DALL-E
        response = self.client.images.generate(
            model=OPENAI_IMAGE_MODEL,
            prompt=full_prompt,
            size=OPENAI_IMAGE_SIZE,
            quality=OPENAI_IMAGE_QUALITY,
            n=1,
        )

        # Get the image URL from response
        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt

        # Download and save the image locally
        filename = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        local_path = IMAGES_DIR / filename

        async with httpx.AsyncClient() as client:
            img_response = await client.get(image_url)
            img_response.raise_for_status()
            
            with open(local_path, "wb") as f:
                f.write(img_response.content)

        return str(local_path), image_url, filename

    async def refine_2d_image(
        self,
        original_prompt: str,
        refinement_text: str,
        original_image_path: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Refine an existing 2D image based on user feedback.
        Creates a new variation incorporating the refinement instructions.
        
        Args:
            original_prompt: The original prompt used to generate the image
            refinement_text: User's refinement instructions
            original_image_path: Path to the original image (for reference)
            
        Returns:
            Tuple of (local_file_path, openai_url, filename)
        """
        # Build refined prompt combining original and refinement
        refined_prompt = f"{original_prompt}\n\nREFINEMENTS TO APPLY:\n{refinement_text}"
        
        # Generate new image with refinements
        return await self.generate_2d_image(refined_prompt)

    def validate_api_key(self) -> bool:
        """
        Validate that the OpenAI API key is working.
        
        Returns:
            True if API key is valid, False otherwise
        """
        try:
            # Make a simple API call to validate the key
            self.client.models.list()
            return True
        except Exception:
            return False


# Singleton instance
_openai_service: Optional[OpenAIService] = None


def get_openai_service() -> OpenAIService:
    """
    Get or create the OpenAI service singleton.
    
    Returns:
        OpenAIService instance
    """
    global _openai_service
    if _openai_service is None:
        _openai_service = OpenAIService()
    return _openai_service
