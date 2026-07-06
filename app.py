from flask import Flask
from sqlalchemy import text

from config import Config
from database import db
import models  # Importa los modelos para que SQLAlchemy los registre
from routes.auth_routes import auth_bp

app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)
app.register_blueprint(auth_bp)


def ensure_schema():
    # Minimal migration support for existing SQLite databases.
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
    app.run(debug=True)