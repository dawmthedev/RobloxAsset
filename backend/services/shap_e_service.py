"""
Shap-E Service for 3D prototype generation.
Uses the official Shap-E pipeline for image-to-3D conversion.

Torch and Shap-E are treated as *optional* dependencies so that the
rest of the API (2D generation, gallery, Meshy, etc.) can run even
if the local 3D pipeline is not installed. The router checks the
``is_available`` method before attempting to generate prototypes.
"""

import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

import numpy as np
from PIL import Image
import imageio

from config import SHAP_E_MODEL_PATH, SHAP_E_DEVICE, PROTOTYPES_DIR

# Torch is optional. If it is not installed we fall back to CPU-only
# behavior and report that Shap-E is not available via is_available().
try:  # pragma: no cover - environment dependent
    import torch  # type: ignore
except ImportError:  # pragma: no cover - handled gracefully at runtime
    torch = None


class ShapEService:
    """
    Service class for Shap-E 3D prototype generation.
    Converts 2D images into low-poly 3D prototypes with turntable previews.
    """

    def __init__(self):
        """Initialize Shap-E models and device configuration."""
        if torch is not None:
            # Respect configured device but fall back to CPU if CUDA is unavailable.
            if SHAP_E_DEVICE.lower() == "cuda" and not torch.cuda.is_available():
                self.device = torch.device("cpu")
            else:
                self.device = torch.device(SHAP_E_DEVICE)
        else:
            # Torch not installed – service will report unavailable but
            # the rest of the API can still import this module.
            self.device = "cpu"
        self.xm = None
        self.model = None
        self.diffusion = None
        self._initialized = False

    def _lazy_init(self):
        """
        Lazily initialize Shap-E models to avoid loading on import.
        Models are loaded only when first needed.
        """
        if self._initialized:
            return

        try:
            from shap_e.diffusion.sample import sample_latents
            from shap_e.diffusion.gaussian_diffusion import diffusion_from_config
            from shap_e.models.download import load_model, load_config
            from shap_e.util.notebooks import decode_latent_mesh, decode_latent_images

            # Store imports for later use
            self._sample_latents = sample_latents
            self._decode_latent_mesh = decode_latent_mesh
            self._decode_latent_images = decode_latent_images

            # Load the transmitter model (for encoding images)
            self.xm = load_model("transmitter", device=self.device)
            
            # Load the image-to-3D model
            self.model = load_model("image300M", device=self.device)
            
            # Load diffusion configuration
            self.diffusion = diffusion_from_config(load_config("diffusion"))

            self._initialized = True
            print(f"Shap-E models loaded successfully on {self.device}")

        except ImportError as e:
            raise ImportError(
                f"Shap-E is not installed. Please install it with: "
                f"pip install shap-e\n"
                f"Original error: {e}"
            )

    def _load_and_preprocess_image(self, image_path: str) -> Image.Image:
        """
        Load and preprocess an image for Shap-E input.
        
        Args:
            image_path: Path to the input image
            
        Returns:
            Preprocessed PIL Image
        """
        img = Image.open(image_path).convert("RGB")
        
        # Resize to 256x256 as expected by Shap-E
        img = img.resize((256, 256), Image.Resampling.LANCZOS)
        
        return img

    def _generate_turntable_gif(
        self, 
        mesh, 
        output_path: str, 
        num_frames: int = 36,
        size: Tuple[int, int] = (256, 256)
    ) -> str:
        """
        Generate a turntable GIF preview of the 3D mesh.
        
        Args:
            mesh: The decoded mesh object
            output_path: Path to save the GIF
            num_frames: Number of frames in the rotation
            size: Size of each frame
            
        Returns:
            Path to the generated GIF
        """
        frames = []
        
        for i in range(num_frames):
            angle = (i / num_frames) * 360
            # Render the mesh from different angles
            # This is a simplified version - actual implementation depends on mesh format
            frame = self._render_mesh_frame(mesh, angle, size)
            frames.append(frame)
        
        # Save as GIF
        imageio.mimsave(output_path, frames, duration=0.1, loop=0)
        
        return output_path

    def _render_mesh_frame(
        self, 
        mesh, 
        angle: float, 
        size: Tuple[int, int]
    ) -> np.ndarray:
        """
        Render a single frame of the mesh at a given angle.
        
        Args:
            mesh: The mesh object to render
            angle: Rotation angle in degrees
            size: Output image size
            
        Returns:
            Rendered frame as numpy array
        """
        # Placeholder implementation - actual rendering depends on mesh format
        # In production, use trimesh or pyrender for proper rendering
        try:
            import trimesh
            from trimesh import viewer
            
            # Convert to trimesh if needed
            if hasattr(mesh, 'tri_mesh'):
                tm = mesh.tri_mesh()
            else:
                # Create a simple placeholder frame
                frame = np.ones((*size, 3), dtype=np.uint8) * 200
                return frame
            
            # Rotate mesh
            rotation = trimesh.transformations.rotation_matrix(
                np.radians(angle), [0, 1, 0]
            )
            tm.apply_transform(rotation)
            
            # Render (simplified - actual implementation would use proper renderer)
            scene = tm.scene()
            png = scene.save_image(resolution=size)
            frame = np.array(Image.open(png))
            
            return frame
            
        except Exception:
            # Return placeholder frame if rendering fails
            frame = np.ones((*size, 3), dtype=np.uint8) * 200
            return frame

    def _save_mesh_as_obj(self, mesh, output_path: str) -> str:
        """
        Save the mesh as an OBJ file.
        
        Args:
            mesh: The decoded mesh object
            output_path: Path to save the OBJ file
            
        Returns:
            Path to the saved OBJ file
        """
        try:
            # Use Shap-E's built-in mesh export
            if hasattr(mesh, 'write_obj'):
                with open(output_path, 'w') as f:
                    mesh.write_obj(f)
            elif hasattr(mesh, 'tri_mesh'):
                # Convert to trimesh and export
                tm = mesh.tri_mesh()
                tm.export(output_path)
            else:
                # Fallback: try to extract vertices and faces
                vertices = mesh.verts.cpu().numpy()
                faces = mesh.faces.cpu().numpy()
                
                with open(output_path, 'w') as f:
                    for v in vertices:
                        f.write(f"v {v[0]} {v[1]} {v[2]}\n")
                    for face in faces:
                        f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
                        
        except Exception as e:
            print(f"Warning: Could not save mesh as OBJ: {e}")
            # Create empty OBJ file as placeholder
            with open(output_path, 'w') as f:
                f.write("# Placeholder OBJ file\n")
                f.write("# Mesh export failed\n")
        
        return output_path

    async def generate_prototype(
        self, 
        image_path: str,
        guidance_scale: float = 15.0,
        num_inference_steps: int = 64
    ) -> Tuple[str, str, str, str]:
        """
        Generate a 3D prototype from a 2D image using Shap-E.
        
        Args:
            image_path: Path to the input 2D image
            guidance_scale: Classifier-free guidance scale
            num_inference_steps: Number of diffusion steps
            
        Returns:
            Tuple of (obj_path, gif_path, obj_filename, gif_filename)
        """
        # Lazy load models
        self._lazy_init()
        
        # Load and preprocess image
        image = self._load_and_preprocess_image(image_path)
        
        # Generate unique filenames
        base_name = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        obj_filename = f"{base_name}.obj"
        gif_filename = f"{base_name}.gif"
        
        obj_path = PROTOTYPES_DIR / obj_filename
        gif_path = PROTOTYPES_DIR / gif_filename
        
        # Sample latents from the image
        batch_size = 1
        latents = self._sample_latents(
            batch_size=batch_size,
            model=self.model,
            diffusion=self.diffusion,
            guidance_scale=guidance_scale,
            model_kwargs=dict(images=[image]),
            progress=True,
            clip_denoised=True,
            use_fp16=True,
            use_karras=True,
            karras_steps=num_inference_steps,
            sigma_min=1e-3,
            sigma_max=160,
            s_churn=0,
        )
        
        # Decode latent to mesh
        for latent in latents:
            mesh = self._decode_latent_mesh(self.xm, latent).tri_mesh()
            
            # Save as OBJ
            self._save_mesh_as_obj(mesh, str(obj_path))
            
            # Generate turntable GIF
            self._generate_turntable_gif(mesh, str(gif_path))
        
        return str(obj_path), str(gif_path), obj_filename, gif_filename

    def is_available(self) -> bool:
        """
        Check if Shap-E is available and can be initialized.
        
        Returns:
            True if Shap-E is available, False otherwise
        """
        # Torch must be present first
        if torch is None:
            return False

        try:
            import shap_e  # type: ignore
            return True
        except ImportError:
            return False


# Singleton instance
_shap_e_service: Optional[ShapEService] = None


def get_shap_e_service() -> ShapEService:
    """
    Get or create the Shap-E service singleton.
    
    Returns:
        ShapEService instance
    """
    global _shap_e_service
    if _shap_e_service is None:
        _shap_e_service = ShapEService()
    return _shap_e_service
