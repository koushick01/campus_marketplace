from datetime import datetime
from extensions import db


class Listing(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price       = db.Column(db.Numeric(10, 2), nullable=False)
    category    = db.Column(db.String(50), nullable=False)
    image         = db.Column(db.String(200))
    user_id       = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    status        = db.Column(db.String(20), default="available", nullable=False)
    condition     = db.Column(db.String(20), nullable=True)
    is_negotiable = db.Column(db.Boolean, default=False)

    user = db.relationship("User", backref="listings")

    def __repr__(self):
        return f"<Listing id={self.id} title={self.title!r} price={self.price}>"
