import os

from flask import Flask, request
from sqlalchemy import text

from config import Config
from database import db
import models  # Importa los modelos para que SQLAlchemy los registre
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp

app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)


@app.after_request
def apply_security_headers(response):
    if not app.config.get("SECURITY_HEADERS_ENABLED", True):
        return response

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "media-src 'self' blob:; "
        "base-uri 'none'; "
        "frame-ancestors 'none'"
    )

    if app.config.get("FLASK_DEBUG", False) is False and request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    return response


def ensure_schema():
    # Minimal migration support only for pre-existing SQLite databases.
    if db.engine.url.get_backend_name() != "sqlite":
        return

    with db.engine.begin() as connection:
        columns = connection.execute(text("PRAGMA table_info(users)"))
        column_names = {row[1] for row in columns}

        if "face_hash" not in column_names:
            connection.execute(text("ALTER TABLE users ADD COLUMN face_hash VARCHAR(64)"))

        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_face_hash ON users (face_hash)"
            )
        )

with app.app_context():
    db.create_all()
    ensure_schema()

if __name__ == "__main__":
    app.run(
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "5000")),
        debug=app.config.get("FLASK_DEBUG", False)
    )