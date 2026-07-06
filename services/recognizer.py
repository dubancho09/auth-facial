import cv2
import numpy as np

from insightface.app import FaceAnalysis


class FaceRecognizer:

    def __init__(self):

        self.app = FaceAnalysis(
            name="buffalo_l"
        )

        try:
            self.app.prepare(
                ctx_id=0,
                det_size=(640, 640)
            )
        except Exception:
            # Fallback for environments without GPU providers.
            self.app.prepare(
                ctx_id=-1,
                det_size=(640, 640)
            )

    def get_embedding(self, image):

        faces = self.app.get(image)

        if len(faces) == 0:
            raise Exception("No se detectó ningún rostro.")

        if len(faces) > 1:
            raise Exception("Se detectaron múltiples rostros.")

        face = faces[0]

        return face.embedding