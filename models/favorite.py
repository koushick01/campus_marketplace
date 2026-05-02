from extensions import db


class Favorite(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listing.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "listing_id", name="uq_favorite_user_listing"),
    )

    def __repr__(self):
        return f"<Favorite user={self.user_id} listing={self.listing_id}>"
