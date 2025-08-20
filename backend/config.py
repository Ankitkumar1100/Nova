import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Flask settings
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))

# STT/TTS settings
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "en-US")
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "en")

# Reminders storage
USE_SQLITE = os.getenv("USE_SQLITE", "true").lower() == "true"
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(os.path.dirname(__file__), "data", "reminders.db"))

# Paths
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
TMP_DIR = os.path.join(BASE_DIR, "tmp")

# Create needed directories if not exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

# Weather
WEATHER_PROVIDER = os.getenv("WEATHER_PROVIDER", "open-meteo")

# Security / API keys (optional)
# Example: GOOGLE_APPLICATION_CREDENTIALS for Google Cloud STT, not used by default 