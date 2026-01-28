import os
from dotenv import load_dotenv

load_dotenv()

# LINE Messaging API
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# LINE Login
LINE_LOGIN_CHANNEL_ID = os.getenv("LINE_LOGIN_CHANNEL_ID")
LINE_LOGIN_CHANNEL_SECRET = os.getenv("LINE_LOGIN_CHANNEL_SECRET")
LINE_LOGIN_REDIRECT_URI = os.getenv("LINE_LOGIN_REDIRECT_URI", "http://localhost:8000/auth/callback")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Database (Turso)
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Session
SESSION_EXPIRE_DAYS = 7
SESSION_COOKIE_NAME = "session_id"
