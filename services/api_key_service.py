import hashlib
import secrets
from datetime import datetime, timedelta

from models import ApiKey
from database import db


class ApiKeyService:

    ALLOWED_SCOPES = {
        "admin:login",
        "plugin:token"
    }

    @staticmethod
    def _normalize_scopes(scopes):
        if not scopes:
            return []

        normalized = []
        for scope in scopes:
            scope = (scope or "").strip().lower()
            if not scope:
                continue
            if scope not in ApiKeyService.ALLOWED_SCOPES:
                raise ValueError(f"Scope no permitido: {scope}")
            if scope not in normalized:
                normalized.append(scope)

        if not normalized:
            raise ValueError("Debes indicar al menos un scope valido.")

        return normalized

    @staticmethod
    def _scopes_to_string(scopes):
        return ",".join(sorted(scopes))

    @staticmethod
    def _scopes_from_string(scopes_raw):
        if not scopes_raw:
            return []
        return [item.strip() for item in scopes_raw.split(",") if item.strip()]

    @staticmethod
    def _hash_key(raw_key):
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_raw_key(prefix):
        secret = secrets.token_urlsafe(32)
        return f"ocr_{prefix}_{secret}"

    @staticmethod
    def _extract_prefix(raw_key):
        if not raw_key:
            return None

        parts = raw_key.split("_", 2)
        if len(parts) != 3 or parts[0] != "ocr":
            return None

        prefix = parts[1].strip()
        if len(prefix) < 8:
            return None

        return prefix

    def create_key(self, name, scopes, expires_in_days=None, client_id=None):
        name = (name or "").strip()
        if len(name) < 3:
            raise ValueError("El nombre de la API key debe tener al menos 3 caracteres.")

        normalized_scopes = self._normalize_scopes(scopes)

        if expires_in_days is None:
            expires_at = None
        else:
            expires_in_days = int(expires_in_days)
            if expires_in_days < 1 or expires_in_days > 3650:
                raise ValueError("expires_in_days debe estar entre 1 y 3650.")
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        client_id = (client_id or "").strip() or None

        for _ in range(5):
            prefix = secrets.token_hex(6)
            if ApiKey.query.filter_by(key_prefix=prefix).first() is not None:
                continue

            raw_key = self._build_raw_key(prefix)
            key_hash = self._hash_key(raw_key)

            api_key = ApiKey(
                name=name,
                key_prefix=prefix,
                key_hash=key_hash,
                scopes=self._scopes_to_string(normalized_scopes),
                client_id=client_id,
                is_active=True,
                expires_at=expires_at
            )
            db.session.add(api_key)
            db.session.commit()
            return api_key, raw_key

        raise RuntimeError("No fue posible generar una API key unica.")

    def verify_key(self, raw_key, required_scopes=None, client_id=None, remote_ip=None):
        prefix = self._extract_prefix(raw_key)
        if not prefix:
            return None, "Formato de API key invalido."

        api_key = ApiKey.query.filter_by(key_prefix=prefix).first()
        if api_key is None:
            return None, "API key invalida."

        provided_hash = self._hash_key(raw_key)
        if not secrets.compare_digest(provided_hash, api_key.key_hash):
            return None, "API key invalida."

        if not api_key.is_active or api_key.revoked_at is not None:
            return None, "API key revocada."

        now = datetime.utcnow()
        if api_key.expires_at is not None and api_key.expires_at <= now:
            return None, "API key expirada."

        required_scopes = self._normalize_scopes(required_scopes or []) if required_scopes else []
        key_scopes = self._scopes_from_string(api_key.scopes)

        for required_scope in required_scopes:
            if required_scope not in key_scopes:
                return None, "API key sin permisos para esta operacion."

        client_id = (client_id or "").strip() or None
        if client_id and api_key.client_id and api_key.client_id != client_id:
            return None, "API key no autorizada para este client_id."

        api_key.last_used_at = now
        if remote_ip:
            api_key.last_used_ip = remote_ip
        db.session.commit()

        return api_key, None

    def list_keys(self):
        keys = ApiKey.query.order_by(ApiKey.created_at.desc()).all()
        data = []

        for key in keys:
            data.append({
                "id": key.id,
                "name": key.name,
                "key_prefix": key.key_prefix,
                "scopes": self._scopes_from_string(key.scopes),
                "client_id": key.client_id,
                "is_active": key.is_active,
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "revoked_at": key.revoked_at.isoformat() if key.revoked_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "last_used_ip": key.last_used_ip,
                "created_at": key.created_at.isoformat() if key.created_at else None
            })

        return data

    @staticmethod
    def revoke_key(key_id):
        key = ApiKey.query.get(key_id)
        if key is None:
            raise ValueError("API key no encontrada.")

        if not key.is_active:
            return key

        key.is_active = False
        key.revoked_at = datetime.utcnow()
        db.session.commit()
        return key
