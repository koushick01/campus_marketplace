import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or "campus-mkt-dev-key-replace-in-production"
    SQLALCHEMY_DATABASE_URI = "sqlite:///marketplace.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
    MAX_CONTENT_LENGTH = 500 * 1024  # 500 KB
