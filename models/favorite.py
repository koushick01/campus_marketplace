from extensions import db


class Favorite(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer)
    listing_id = db.Column(db.Integer)
