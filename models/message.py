from datetime import datetime
from extensions import db


class Message(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    listing_id  = db.Column(db.Integer, db.ForeignKey("listing.id"), nullable=True)
    text        = db.Column(db.Text, nullable=False)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)
    is_read     = db.Column(db.Boolean, default=False)

    sender  = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])
    listing  = db.relationship("Listing", foreign_keys=[listing_id])

    def __repr__(self):
        return f"<Message id={self.id} from={self.sender_id} to={self.receiver_id}>"
