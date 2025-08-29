import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SQLite database path
DB_PATH = BASE_DIR / "aura.db"

# External API keys
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AuraApp/0.1")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

THECOMPANIESAPI_KEY = os.getenv("THECOMPANIESAPI_KEY", "")
ABSTRACT_API_KEY = os.getenv("ABSTRACT_API_KEY", "") 