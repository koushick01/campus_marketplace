from datetime import datetime
from extensions import db


class Message(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer)
    receiver_id = db.Column(db.Integer)
    listing_id  = db.Column(db.Integer)
    text        = db.Column(db.Text)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)
