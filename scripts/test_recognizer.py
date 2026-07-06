import sys
from pathlib import Path

import cv2
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.recognizer import FaceRecognizer


def load_image(image_name: str):
    image_path = PROJECT_ROOT / "test_images" / image_name

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    return image


recognizer = FaceRecognizer()

# Cargar imágenes
image1 = load_image("image.jpeg")
image2 = load_image("france.jpeg")

# Obtener embeddings
embedding1 = recognizer.get_embedding(image1)
embedding2 = recognizer.get_embedding(image2)

print(f"Embedding 1 shape: {embedding1.shape}")
print(f"Embedding 2 shape: {embedding2.shape}")

# Calcular similitud
similarity = cosine_similarity(
    embedding1.reshape(1, -1),
    embedding2.reshape(1, -1)
)[0][0]

print("\n==============================")
print(f"Similarity: {similarity:.4f}")
print("==============================")

# Interpretación
if similarity >= 0.80:
    print("✅ Casi seguro es la misma persona")
elif similarity >= 0.70:
    print("✅ Muy probable que sea la misma persona")
elif similarity >= 0.60:
    print("⚠️ Posible coincidencia")
else:
    print("❌ Probablemente son personas diferentes")