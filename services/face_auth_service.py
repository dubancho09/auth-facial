import base64
import hashlib

import cv2
import numpy as np

from database import db
from models import LoginHistory, User
from services.recognizer import FaceRecognizer


class FaceAuthService:

    def __init__(self, similarity_threshold=0.45):
        self.recognizer = FaceRecognizer()
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def decode_frame(data_url):
        if not data_url:
            raise ValueError("No se recibió ningún frame.")

        if "," in data_url:
            _, encoded = data_url.split(",", 1)
        else:
            encoded = data_url

        image_bytes = base64.b64decode(encoded)
        buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("No se pudo decodificar la imagen.")

        return image

    @staticmethod
    def _normalize_embedding(embedding):
        emb = np.asarray(embedding, dtype=np.float32)
        norm = np.linalg.norm(emb)

        if norm == 0:
            raise ValueError("Embedding inválido: norma cero.")

        return emb / norm

    def build_face_hash(self, embedding):
        normalized = self._normalize_embedding(embedding)

        # Keep the hash deterministic while reducing tiny floating point noise.
        rounded = np.round(normalized, 6)
        return hashlib.sha256(rounded.tobytes()).hexdigest()

    @staticmethod
    def serialize_embedding(embedding):
        emb = np.asarray(embedding, dtype=np.float32)
        return emb.tobytes()

    @staticmethod
    def deserialize_embedding(blob):
        emb = np.frombuffer(blob, dtype=np.float32)
        return emb

    def register_user(self, nombre, documento, frame_data):
        if not nombre or not documento:
            raise ValueError("Nombre y documento son obligatorios.")

        existing = User.query.filter_by(documento=documento).first()
        if existing:
            raise ValueError("Ya existe un usuario con ese documento.")

        image = self.decode_frame(frame_data)
        embedding = self.recognizer.get_embedding(image)

        face_hash = self.build_face_hash(embedding)

        if User.query.filter_by(face_hash=face_hash).first():
            raise ValueError("Este rostro ya está registrado en el sistema.")

        user = User(
            nombre=nombre.strip(),
            documento=documento.strip(),
            face_hash=face_hash,
            embedding=self.serialize_embedding(embedding)
        )

        db.session.add(user)
        db.session.commit()

        return {
            "id": user.id,
            "nombre": user.nombre,
            "documento": user.documento,
            "face_hash": user.face_hash
        }

    def authenticate(self, frame_data):
        image = self.decode_frame(frame_data)
        probe_embedding = self._normalize_embedding(self.recognizer.get_embedding(image))

        users = User.query.all()

        if len(users) == 0:
            self._store_login_attempt(None, False, 0.0)
            return {
                "authenticated": False,
                "message": "No hay usuarios registrados."
            }

        best_user = None
        best_score = -1.0

        for user in users:
            user_embedding = self.deserialize_embedding(user.embedding)
            user_embedding = self._normalize_embedding(user_embedding)

            score = float(np.dot(probe_embedding, user_embedding))

            if score > best_score:
                best_score = score
                best_user = user

        is_authenticated = best_user is not None and best_score >= self.similarity_threshold
        self._store_login_attempt(best_user.id if is_authenticated else None, is_authenticated, best_score)

        if not is_authenticated:
            return {
                "authenticated": False,
                "score": round(best_score, 4),
                "threshold": self.similarity_threshold,
                "message": "Rostro no reconocido."
            }

        return {
            "authenticated": True,
            "score": round(best_score, 4),
            "threshold": self.similarity_threshold,
            "user": {
                "id": best_user.id,
                "nombre": best_user.nombre,
                "documento": best_user.documento,
                "face_hash": best_user.face_hash
            }
        }

    @staticmethod
    def _store_login_attempt(user_id, resultado, score):
        attempt = LoginHistory(
            user_id=user_id,
            resultado=resultado,
            score=float(score)
        )

        db.session.add(attempt)
        db.session.commit()
