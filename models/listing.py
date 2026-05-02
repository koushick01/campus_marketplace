from datetime import datetime
from extensions import db


class Listing(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(120))
    description = db.Column(db.Text)
    price       = db.Column(db.Float)
    category    = db.Column(db.String(50))
    image       = db.Column(db.String(200))
    user_id     = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
