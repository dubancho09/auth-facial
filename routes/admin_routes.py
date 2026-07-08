import hmac
import os
import re

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from database import db
from models import LoginHistory, User
from services.face_auth_service import FaceAuthService


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
face_auth_service = FaceAuthService(
    duplicate_face_threshold=float(os.getenv("DUPLICATE_FACE_THRESHOLD", "0.92"))
)

_DOCUMENT_PATTERN = re.compile(r"^[A-Za-z0-9._-]{4,30}$")


def _is_admin_authenticated():
    return session.get("admin_authenticated") is True


def _require_admin_session():
    if _is_admin_authenticated():
        return None

    if request.path.startswith("/admin/api/"):
        return jsonify({"ok": False, "error": "No autorizado."}), 401

    return redirect(url_for("admin.login"))


def _error_response(message, status_code):
    return jsonify({"ok": False, "error": message}), status_code


def _validate_admin_payload(nombre, documento):
    if not nombre or not documento:
        raise ValueError("Nombre y documento son obligatorios.")

    nombre = nombre.strip()
    documento = documento.strip()

    if len(nombre) < 2 or len(nombre) > 100:
        raise ValueError("Nombre invalido: debe tener entre 2 y 100 caracteres.")

    if not _DOCUMENT_PATTERN.match(documento):
        raise ValueError("Identificacion invalida: usa 4-30 caracteres alfanumericos, punto, guion o guion bajo.")


@admin_bp.before_request
def admin_before_request():
    open_paths = {"admin.login", "admin.login_submit"}

    if request.endpoint in open_paths:
        return None

    return _require_admin_session()


@admin_bp.get("/")
def home():
    return redirect(url_for("admin.users_panel"))


@admin_bp.get("/login")
def login():
    if _is_admin_authenticated():
        return redirect(url_for("admin.users_panel"))

    return render_template("admin_login.html", error=None)


@admin_bp.post("/login")
def login_submit():
    provided_key = (request.form.get("api_key") or "").strip()
    expected_key = current_app.config.get("ADMIN_PANEL_API_KEY", "")

    if not expected_key:
        return render_template(
            "admin_login.html",
            error="ADMIN_PANEL_API_KEY no esta configurada en el servidor."
        ), 500

    if not hmac.compare_digest(provided_key, expected_key):
        return render_template("admin_login.html", error="API key invalida."), 401

    session["admin_authenticated"] = True
    return redirect(url_for("admin.users_panel"))


@admin_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.get("/users")
def users_panel():
    return render_template("admin_users.html")


@admin_bp.get("/api/users")
def list_users():
    users = User.query.order_by(User.fecha_creacion.desc()).all()

    data = [
        {
            "id": user.id,
            "nombre": user.nombre,
            "documento": user.documento,
            "face_hash": user.face_hash,
            "fecha_creacion": user.fecha_creacion.isoformat() if user.fecha_creacion else None
        }
        for user in users
    ]

    return jsonify({"ok": True, "data": data})


@admin_bp.post("/api/users")
def create_user():
    if not request.is_json:
        return _error_response("Se requiere Content-Type application/json.", 400)

    payload = request.get_json(silent=True) or {}

    try:
        result = face_auth_service.register_user(
            nombre=payload.get("nombre", ""),
            documento=payload.get("documento", ""),
            frame_data=payload.get("frame", "")
        )
    except ValueError as error:
        return _error_response(str(error), 400)
    except Exception:
        current_app.logger.exception("Error interno en /admin/api/users")
        return _error_response("Error interno del servidor.", 500)

    return jsonify({"ok": True, "data": result}), 201


@admin_bp.put("/api/users/<int:user_id>")
def update_user(user_id):
    if not request.is_json:
        return _error_response("Se requiere Content-Type application/json.", 400)

    user = User.query.get(user_id)
    if not user:
        return _error_response("Usuario no encontrado.", 404)

    payload = request.get_json(silent=True) or {}
    nombre = (payload.get("nombre") or "").strip()
    documento = (payload.get("documento") or "").strip()

    try:
        _validate_admin_payload(nombre, documento)
    except ValueError as error:
        return _error_response(str(error), 400)

    existing_document = User.query.filter(User.documento == documento, User.id != user_id).first()
    if existing_document:
        return _error_response("Ya existe un usuario con esa identificacion.", 400)

    user.nombre = nombre
    user.documento = documento

    db.session.commit()

    return jsonify({
        "ok": True,
        "data": {
            "id": user.id,
            "nombre": user.nombre,
            "documento": user.documento,
            "face_hash": user.face_hash,
            "fecha_creacion": user.fecha_creacion.isoformat() if user.fecha_creacion else None
        }
    })


@admin_bp.delete("/api/users/<int:user_id>")
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return _error_response("Usuario no encontrado.", 404)

    LoginHistory.query.filter_by(user_id=user_id).update({"user_id": None})
    db.session.delete(user)
    db.session.commit()

    return jsonify({"ok": True})
