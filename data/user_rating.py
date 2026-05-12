from .db import db

class UserRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    rater_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    value = db.Column(db.Integer)
