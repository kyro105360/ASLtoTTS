import os
import pickle
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.p"
os.environ.setdefault("MPLCONFIGDIR", str(BASE_DIR / ".matplotlib"))

LABELS = {
    0: "a",
    1: "b",
    2: "c",
    3: "d",
    4: "e",
    5: "f",
    6: "g",
    7: "h",
    8: "i",
    9: "j",
    10: "k",
    11: "l",
    12: "m",
    13: "n",
    14: "o",
    15: "p",
    16: "q",
    17: "r",
    18: "s",
    19: "t",
    20: "u",
    21: "v",
    22: "w",
    23: "x",
    24: "y",
    25: "z",
    26: " ",
    27: "\b",
    28: "C",
}


def load_model(model_path: Path = MODEL_PATH):
    with Path(model_path).open("rb") as model_file:
        return pickle.load(model_file)["modelT"]


def build_hand_detector():
    import mediapipe

    return mediapipe.solutions.hands.Hands(
        static_image_mode=True,
        min_detection_confidence=0.3,
    )


def extract_landmark_vector(multi_hand_landmarks: Iterable | None):
    if not multi_hand_landmarks:
        return None

    for hand_landmarks in multi_hand_landmarks:
        points = [(landmark.x, landmark.y) for landmark in hand_landmarks.landmark]
        if len(points) != 21:
            continue

        min_x = min(x for x, _ in points)
        min_y = min(y for _, y in points)

        normalized = []
        for x, y in points:
            normalized.extend((x - min_x, y - min_y))

        return np.asarray(normalized, dtype=np.float32)

    return None


@dataclass
class PredictorEngine:
    model: Callable
    hand_detector: object
    labels: dict[int, str] = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = LABELS

    def extract_features(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hand_detector.process(frame_rgb)
        return extract_landmark_vector(getattr(results, "multi_hand_landmarks", None))

    def predict(self, frame):
        features = self.extract_features(frame)
        if features is None or features.size != 42:
            return ""

        prediction = self.model([np.expand_dims(features, axis=0)])
        predicted_index = int(np.argmax(prediction[0]))
        return self.labels.get(predicted_index, "")


@lru_cache(maxsize=1)
def get_engine():
    return PredictorEngine(
        model=load_model(),
        hand_detector=build_hand_detector(),
    )


def runCamera(frame, engine: PredictorEngine | None = None):
    return (engine or get_engine()).predict(frame)
