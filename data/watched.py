from datetime import datetime
from .db import db

class Watched(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    movie_id = db.Column(db.Integer, db.ForeignKey("movie.id"))

    created_at = db.Column(db.DateTime)

    user = db.relationship("User")
    movie = db.relationship("Movie")  # ← ВАЖНО
