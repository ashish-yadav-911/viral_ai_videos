# config.py (Updated)
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- File Paths ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
MUSIC_DIR = os.path.join(BASE_DIR, 'music')
# Ensure asset directory exists
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)

# --- Database ---
DEFAULT_DB_FILE = os.path.join(BASE_DIR, 'youtube_automator.db')
DATABASE_FILE = os.getenv('DATABASE_FILE', DEFAULT_DB_FILE)

# --- Google API (Disabled for now) ---
# SCOPES = [
#     'https://www.googleapis.com/auth/spreadsheets', # Removed
#     'https://www.googleapis.com/auth/youtube.upload' # Keep scope if planning upload later
# ]
# GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID') # Removed
# WORKSHEET_NAME = os.getenv('WORKSHEET_NAME', 'Sheet1') # Removed

# --- OpenAI ---
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_GPT_MODEL = "gpt-4-turbo-preview"
OPENAI_IMAGE_MODEL = "dall-e-3"
OPENAI_WHISPER_MODEL = "whisper-1"

# --- ElevenLabs ---
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
DEFAULT_VOICE_ID = os.getenv('ELEVENLABS_DEFAULT_VOICE_ID')
AVAILABLE_VOICE_IDS = {
    "Default": DEFAULT_VOICE_ID,
    "Adam": "pNInz6obpgDQGcFmaJgB",
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
}
# --- Cartesia ---
CARTESIA_API_KEY = os.getenv('CARTESIA_API_KEY')
# Cartesia models (check their docs for latest/best options)
DEFAULT_MODEL_ID_CARTESIA = "sonic-english"
# Cartesia voices (these are examples, find actual IDs/names)
DEFAULT_VOICE_NAME_CARTESIA = "default" # Or specific voice name/embedding

# --- Deepgram ---
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
# Deepgram Aura models (check their docs)
DEFAULT_MODEL_ID_DEEPGRAM = "aura-asteria-en" # Example voice model

TTS_PROVIDER_PRIORITY = ['cartesia', 'deepgram', 'elevenlabs']


# --- Pexels ---
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')

# --- Video Generation ---
DEFAULT_IMAGE_STYLE = "photorealistic"
AVAILABLE_IMAGE_STYLES = ["photorealistic", "cinematic", "anime", "cartoonish", "abstract", "minimalist"]
CAPTION_STYLES = {
    "Subtle": {"font": "Arial", "fontsize": 24, "color": "white", "stroke_color": "black", "stroke_width": 1},
    "Trendy": {"font": "Impact", "fontsize": 30, "color": "yellow", "stroke_color": "black", "stroke_width": 2},
    "Fiery": {"font": "Georgia", "fontsize": 28, "color": "orange", "bg_color": (0,0,0,0.5)},
}
DEFAULT_CAPTION_STYLE = "Subtle"
WORDS_PER_CAPTION_CHUNK = 3
IMAGES_PER_SCRIPT = 8
IMAGE_SIZE = "1024x1024"
VIDEO_ASPECT_RATIO = (16, 9)
VIDEO_FPS = 24

# --- Automation ---
VIDEOS_TO_GENERATE_PER_RUN = 2
VIDEOS_TO_UPLOAD_PER_DAY = 2 # Still relevant for orchestrator logic, just won't trigger upload

# --- Notifications ---
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
RECIPIENT_EMAILS = [email.strip() for email in [os.getenv('NOTIFICATION_RECIPIENT_EMAIL_1'), os.getenv('NOTIFICATION_RECIPIENT_EMAIL_2')] if email]

# --- YouTube Upload (Settings Disabled) ---
DEFAULT_VIDEO_PRIVACY = "private"
# YOUTUBE_API_SERVICE_NAME = 'youtube'
# YOUTUBE_API_VERSION = 'v3'

# --- Flask ---
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-prod') # Provide a default for dev
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5001))

# --- Basic Input Validation ---
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found in .env file.")
if not DATABASE_FILE:
     print("Warning: DATABASE_FILE not configured.")
# Add more checks as needed