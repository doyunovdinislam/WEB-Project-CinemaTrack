from flask_login import UserMixin
from .db import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

    display_name = db.Column(db.String(100))
    description = db.Column(db.String(300))

    avatar = db.Column(db.String(200), default="default.png")
