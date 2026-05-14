from .db import db

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)
    movie_id = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "movie_id", name="unique_favorite"),
    )
