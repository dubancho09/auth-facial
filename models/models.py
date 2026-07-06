from datetime import datetime

from database import db


class User(db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(100),
        nullable=False
    )

    documento = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    embedding = db.Column(
        db.LargeBinary,
        nullable=False
    )

    fecha_creacion = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class LoginHistory(db.Model):

    __tablename__ = "login_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    fecha = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    resultado = db.Column(
        db.Boolean,
        nullable=False
    )

    score = db.Column(
        db.Float
    )