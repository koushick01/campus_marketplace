import os
from flask import Flask
from dotenv import load_dotenv
from config import Config
from extensions import db, login_manager

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager.login_view = "login"
login_manager.init_app(app)

from models import User  # noqa: E402

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

import views  # noqa: E402, F401

with app.app_context():
    db.create_all()
