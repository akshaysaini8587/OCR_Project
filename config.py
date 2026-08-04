import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "root1"),
        "database": os.getenv("DB_NAME", "ocr_db")
    }
    POPPLER_PATH = os.getenv("POPPLER_PATH", None)