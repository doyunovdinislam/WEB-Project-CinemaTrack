from datetime import datetime
from .db import db

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    text = db.Column(db.Text)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    movie_id = db.Column(db.Integer, db.ForeignKey("movie.id"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)



    user = db.relationship("User")  # ← ВАЖНО

