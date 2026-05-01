import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "devkey")
    SQLALCHEMY_DATABASE_URI = "sqlite:///marketplace.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "static/uploads"
    MAX_CONTENT_LENGTH = 500 * 1024  # 500KB image limit
