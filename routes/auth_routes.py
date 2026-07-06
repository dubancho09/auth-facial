import hmac
from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, render_template, request

from services.face_auth_service import FaceAuthService
from services.plugin_security_service import PluginSecurityService
from services.rate_limiter import InMemoryRateLimiter


auth_bp = Blueprint("auth", __name__)
face_auth_service = FaceAuthService()
rate_limiter = InMemoryRateLimiter()


def _error_response(message, status_code):
    return jsonify({"ok": False, "error": message}), status_code


def _require_json_body():
    if not request.is_json:
        raise ValueError("Se requiere Content-Type application/json.")


def _remote_ip():
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return forwarded or (request.remote_addr or "unknown")


def _enforce_rate_limit(bucket_name, per_window):
    key = f"{bucket_name}:{_remote_ip()}"
    allowed, retry_after = rate_limiter.allow(
        key=key,
        limit=per_window,
        window_seconds=current_app.config.get("RATE_LIMIT_WINDOW_SECONDS", 60)
    )

    if not allowed:
        response = jsonify({"ok": False, "error": "Demasiadas solicitudes. Intenta nuevamente en unos segundos."})
        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)
        return response

    return None


def _validate_origin(origin):
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Origin invalido.")

    allowed = {
        item.strip() for item in current_app.config.get("PLUGIN_ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    }

    if allowed and origin not in allowed:
        raise ValueError("Origin no permitido.")


def _require_register_api_key_if_configured():
    expected = current_app.config.get("REGISTER_API_KEY", "")
    if not expected:
        return

    received = request.headers.get("X-Register-Api-Key", "")
    if not hmac.compare_digest(expected, received):
        raise PermissionError("No autorizado para registrar usuarios.")


def _plugin_security_service():
    return PluginSecurityService(
        secret_key=current_app.config.get("SECRET_KEY", "change-this-in-production")
    )


def _resolve_plugin_context():
    plugin_mode = request.args.get("plugin") == "1"
    opener_origin = "*"

    if not plugin_mode:
        return {
            "plugin_mode": False,
            "opener_origin": opener_origin
        }

    security_enabled = current_app.config.get("PLUGIN_SECURITY_ENABLED", True)

    if not security_enabled:
        opener_origin = request.args.get("origin", "*")
        return {
            "plugin_mode": True,
            "opener_origin": opener_origin
        }

    token = request.args.get("token", "")
    if not token:
        raise ValueError("Falta token de lanzamiento del plugin.")

    security_service = _plugin_security_service()
    payload = security_service.verify_launch_token(
        token=token,
        max_age_seconds=current_app.config.get("PLUGIN_TOKEN_TTL_SECONDS", 120)
    )

    opener_origin = payload.get("origin", "*")

    return {
        "plugin_mode": True,
        "opener_origin": opener_origin,
        "client_id": payload.get("client_id")
    }


@auth_bp.get("/")
def index():
    try:
        plugin_context = _resolve_plugin_context()
        return render_template("index.html", plugin_context=plugin_context)
    except Exception as error:
        return f"Acceso bloqueado: {str(error)}", 403


@auth_bp.post("/api/plugin/token")
def issue_plugin_token():
    limited = _enforce_rate_limit(
        bucket_name="token",
        per_window=current_app.config.get("RATE_LIMIT_TOKEN_PER_WINDOW", 20)
    )
    if limited is not None:
        return limited

    if not current_app.config.get("PLUGIN_SECURITY_ENABLED", True):
        return _error_response("La seguridad de plugin esta deshabilitada.", 400)

    try:
        _require_json_body()
    except ValueError as error:
        return _error_response(str(error), 400)

    payload = request.get_json(silent=True) or {}
    client_id = (payload.get("client_id") or "").strip()
    origin = (payload.get("origin") or "").strip()
    api_key = request.headers.get("X-Plugin-Api-Key", "").strip()

    if not client_id or not origin:
        return _error_response("client_id y origin son obligatorios.", 400)

    try:
        _validate_origin(origin)
    except ValueError as error:
        return _error_response(str(error), 400)

    clients = PluginSecurityService.parse_clients(current_app.config.get("PLUGIN_CLIENTS", ""))
    if not clients:
        return _error_response("No hay clientes de plugin configurados.", 500)

    expected_key = clients.get(client_id)
    if not expected_key or not hmac.compare_digest(expected_key, api_key):
        return _error_response("Cliente no autorizado.", 401)

    token = _plugin_security_service().issue_launch_token(client_id=client_id, origin=origin)

    return jsonify({
        "ok": True,
        "data": {
            "token": token,
            "expires_in": current_app.config.get("PLUGIN_TOKEN_TTL_SECONDS", 120)
        }
    })


@auth_bp.post("/api/stream/register")
def stream_register():
    limited = _enforce_rate_limit(
        bucket_name="register",
        per_window=current_app.config.get("RATE_LIMIT_REGISTER_PER_WINDOW", 10)
    )
    if limited is not None:
        return limited

    try:
        _require_json_body()
        _require_register_api_key_if_configured()
    except ValueError as error:
        return _error_response(str(error), 400)
    except PermissionError as error:
        return _error_response(str(error), 401)

    payload = request.get_json(silent=True) or {}

    try:
        result = face_auth_service.register_user(
            nombre=payload.get("nombre", ""),
            documento=payload.get("documento", ""),
            frame_data=payload.get("frame", "")
        )
        return jsonify({"ok": True, "data": result}), 201
    except ValueError as error:
        return _error_response(str(error), 400)
    except Exception:
        current_app.logger.exception("Error interno en /api/stream/register")
        return _error_response("Error interno del servidor.", 500)


@auth_bp.post("/api/stream/authenticate")
def stream_authenticate():
    limited = _enforce_rate_limit(
        bucket_name="authenticate",
        per_window=current_app.config.get("RATE_LIMIT_AUTH_PER_WINDOW", 180)
    )
    if limited is not None:
        return limited

    try:
        _require_json_body()
    except ValueError as error:
        return _error_response(str(error), 400)

    payload = request.get_json(silent=True) or {}

    try:
        result = face_auth_service.authenticate(
            frame_data=payload.get("frame", "")
        )

        status_code = 200 if result.get("authenticated") else 401
        return jsonify({"ok": result.get("authenticated", False), "data": result}), status_code
    except ValueError as error:
        return _error_response(str(error), 400)
    except Exception:
        current_app.logger.exception("Error interno en /api/stream/authenticate")
        return _error_response("Error interno del servidor.", 500)
