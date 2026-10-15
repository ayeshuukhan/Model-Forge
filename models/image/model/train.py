"""
Trains a lightweight image classifier using simple color/texture
features (mean RGB, brightness, color variance) + RandomForest,
instead of a heavy pretrained CNN.

This keeps the service CPU-only, GPU-free, and avoids downloading
large pretrained weights at build time - the point of this project
is demonstrating how ANY model can be packaged as a K8s microservice,
not achieving state-of-the-art image classification.

Training data: small synthetic colored images per class, generated
procedurally so no external dataset is required.
"""
import os
import numpy as np
from PIL import Image
import joblib
from sklearn.ensemble import RandomForestClassifier

rng = np.random.default_rng(7)
CLASSES = ["cat", "dog", "other"]

# Rough class "signatures" as base colors (cat: orange/tan, dog: brown, other: varied)
BASE_COLORS = {
    "cat": (200, 140, 90),
    "dog": (120, 85, 55),
    "other": (100, 100, 100),
}


def extract_features(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    mean_rgb = arr.mean(axis=(0, 1))
    std_rgb = arr.std(axis=(0, 1))
    brightness = arr.mean()
    return np.concatenate([mean_rgb, std_rgb, [brightness]])


def make_synthetic_image(base_color, noise=40, size=64):
    arr = np.zeros((size, size, 3), dtype=np.float32)
    for c in range(3):
        arr[:, :, c] = base_color[c] + rng.normal(0, noise, (size, size))
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


X, y = [], []
for cls in CLASSES:
    for _ in range(60):
        img = make_synthetic_image(BASE_COLORS[cls])
        X.append(extract_features(img))
        y.append(cls)

X = np.array(X)
clf = RandomForestClassifier(n_estimators=100, random_state=7)
clf.fit(X, y)

out_path = os.path.join(os.path.dirname(__file__), "image_model.joblib")
joblib.dump(clf, out_path)
print(f"Image model trained and saved to {out_path}")
