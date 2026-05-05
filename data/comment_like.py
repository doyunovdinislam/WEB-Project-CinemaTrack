from .db import db

class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer)
    comment_id = db.Column(db.Integer)

    value = db.Column(db.Integer)
