from flask import Blueprint, jsonify, render_template, request

from services.face_auth_service import FaceAuthService


auth_bp = Blueprint("auth", __name__)
face_auth_service = FaceAuthService()


@auth_bp.get("/")
def index():
    return render_template("index.html")


@auth_bp.post("/api/stream/register")
def stream_register():
    payload = request.get_json(silent=True) or {}

    try:
        result = face_auth_service.register_user(
            nombre=payload.get("nombre", ""),
            documento=payload.get("documento", ""),
            frame_data=payload.get("frame", "")
        )
        return jsonify({"ok": True, "data": result}), 201
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@auth_bp.post("/api/stream/authenticate")
def stream_authenticate():
    payload = request.get_json(silent=True) or {}

    try:
        result = face_auth_service.authenticate(
            frame_data=payload.get("frame", "")
        )

        status_code = 200 if result.get("authenticated") else 401
        return jsonify({"ok": result.get("authenticated", False), "data": result}), status_code
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400
