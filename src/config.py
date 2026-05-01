"""Configuration module for AI Takeoff Builder."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Dataset paths
SAMPLE_PROJECTS_DIR = DATA_DIR / "sample_projects"
CHALLENGE_PROJECTS_DIR = DATA_DIR / "challenge_projects"

# API Keys (load from environment only — no hardcoded defaults)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# LLM Configuration
DEFAULT_LLM_MODEL = "gpt-4o"
DEFAULT_LLM_PROVIDER = "openai"  # "openai" or "kimi"

# Fallback to OpenAI
OPENAI_FALLBACK_MODEL = "gpt-4o"
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 8000

# File types
DRAWING_KEYWORDS = ["drawing", "plan", "elevation", "section", "detail"]
SPEC_KEYWORDS = ["spec", "specification"]
SOW_KEYWORDS = ["scope", "sow", "scope of work"]
ADDENDUM_KEYWORDS = ["addendum", "addenda"]
RULES_KEYWORDS = ["rule", "regulation", "standard"]
BREAKOUT_KEYWORDS = ["breakout", "break out"]

# Output template
OUTPUT_TEMPLATE = {
    "project_id": "",
    "trade_scope": "",
    "input_files_used": [],
    "ai_run": {
        "run_id": "",
        "tools_or_models_used": [],
        "assumptions": [],
        "warnings": []
    },
    "line_items": [],
    "evaluation_when_gold_available": None
}

# OCR Configuration
MIN_TEXT_CHARS_FOR_NON_SCANNED = 50
OCR_AUTO_ENABLED = True
OCR_ON_DRAWINGS_ONLY = False
OCR_DPI = 100
OCR_DEFAULT_LANG = "eng"
OCR_DEFAULT_PSM = 11      # Sparse text (best for drawings with scattered text)
OCR_DEFAULT_OEM = 1       # LSTM only (faster)
OCR_PREPROCESS_ENABLED = True   # Light preprocessing for accuracy
OCR_SHARPEN_ENABLED = False     # Skip sharpening for speed
OCR_CONTRAST_ENHANCE = 1.5
OCR_DESKEW_ENABLED = False

# Evaluation thresholds
FUZZY_MATCH_THRESHOLD = 80
QTY_EXACT_THRESHOLD = 5.0    # percent
QTY_CLOSE_THRESHOLD = 10.0   # percent
