from datetime import datetime
from .db import db


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    avg_rating = db.Column(db.Float, default=0)

    title = db.Column(db.String(200))
    description = db.Column(db.Text)

    poster = db.Column(db.String(200))
    poster2 = db.Column(db.String(200))
    video = db.Column(db.String(200))

    genre = db.Column(db.String(100))
    country = db.Column(db.String(100))
    director = db.Column(db.String(100))
    duration = db.Column(db.String(50))

    views = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="movies")
