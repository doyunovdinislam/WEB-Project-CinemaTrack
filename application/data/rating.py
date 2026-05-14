from .db import db

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    movie_id = db.Column(db.Integer, db.ForeignKey("movie.id"))

    value = db.Column(db.Integer)
