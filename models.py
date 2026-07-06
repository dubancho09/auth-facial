from datetime import datetime

from database import db


class User(db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(100), nullable=False)

    documento = db.Column(db.String(30), unique=True, nullable=False)

    face_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)

    embedding = db.Column(db.LargeBinary, nullable=False)

    fecha_creacion = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    login_history = db.relationship(
        "LoginHistory",
        backref="user",
        lazy=True
    )


class LoginHistory(db.Model):

    __tablename__ = "login_history"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    fecha = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    resultado = db.Column(db.Boolean)

    score = db.Column(db.Float)