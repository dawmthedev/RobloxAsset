"""
Configuration module for the 3D Asset Generation Pipeline.
Loads environment variables and provides configuration constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MESHY_API_KEY = os.getenv("MESHY_API_KEY", "")

# Shap-E Configuration
SHAP_E_MODEL_PATH = os.getenv("SHAP_E_MODEL_PATH", "openai/shap-e")
SHAP_E_DEVICE = os.getenv("SHAP_E_DEVICE", "cuda")  # or "cpu"

# Storage Paths
BASE_DIR = Path(__file__).parent
STORAGE_DIR = BASE_DIR / "storage"
IMAGES_DIR = STORAGE_DIR / "images"
PROTOTYPES_DIR = STORAGE_DIR / "prototypes"
FINAL_DIR = STORAGE_DIR / "final"

# Ensure storage directories exist
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
PROTOTYPES_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/gallery.db")

# Meshy API Configuration
MESHY_API_BASE_URL = "https://api.meshy.ai/v2"
MESHY_WEBHOOK_URL = os.getenv("MESHY_WEBHOOK_URL", "")

# OpenAI Configuration
OPENAI_IMAGE_MODEL = "dall-e-3"
OPENAI_IMAGE_SIZE = "1024x1024"
OPENAI_IMAGE_QUALITY = "hd"

# Server Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
