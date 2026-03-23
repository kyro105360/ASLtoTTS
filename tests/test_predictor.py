import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pythonScripts"))

import predictor


class FakeLandmark:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class FakeHandLandmarks:
    def __init__(self, points):
        self.landmark = [FakeLandmark(x, y) for x, y in points]


class FakeHandDetector:
    def __init__(self, multi_hand_landmarks):
        self.multi_hand_landmarks = multi_hand_landmarks
        self.frames = []

    def process(self, frame_rgb):
        self.frames.append(frame_rgb)
        return SimpleNamespace(multi_hand_landmarks=self.multi_hand_landmarks)


class FakeModel:
    def __init__(self, logits):
        self.logits = np.asarray([logits], dtype=np.float32)
        self.calls = []

    def __call__(self, payload):
        self.calls.append(payload)
        return self.logits


def build_points():
    return [(index / 10.0, index / 20.0) for index in range(21)]


class PredictorEngineTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((12, 12, 3), dtype=np.uint8)

    def test_extract_landmark_vector_returns_normalized_42_value_vector(self):
        vector = predictor.extract_landmark_vector([FakeHandLandmarks(build_points())])

        self.assertEqual(vector.shape, (42,))
        self.assertEqual(vector[0], 0.0)
        self.assertEqual(vector[1], 0.0)
        self.assertAlmostEqual(vector[-2], 2.0)
        self.assertAlmostEqual(vector[-1], 1.0)

    def test_extract_landmark_vector_skips_incomplete_hand_and_uses_next_valid_hand(self):
        invalid_hand = FakeHandLandmarks([(0.1, 0.1)] * 20)
        valid_hand = FakeHandLandmarks(build_points())

        vector = predictor.extract_landmark_vector([invalid_hand, valid_hand])

        self.assertIsNotNone(vector)
        self.assertEqual(vector.shape, (42,))

    def test_predict_returns_empty_when_no_hands_are_found(self):
        engine = predictor.PredictorEngine(
            model=FakeModel([0.1, 0.9]),
            hand_detector=FakeHandDetector(None),
        )

        self.assertEqual(engine.predict(self.frame), "")

    def test_predict_uses_cached_engine_model_output(self):
        engine = predictor.PredictorEngine(
            model=FakeModel([0.1, 0.9, 0.2]),
            hand_detector=FakeHandDetector([FakeHandLandmarks(build_points())]),
            labels={0: "a", 1: "b", 2: "c"},
        )

        prediction = engine.predict(self.frame)

        self.assertEqual(prediction, "b")
        self.assertEqual(len(engine.model.calls), 1)
        self.assertEqual(engine.model.calls[0][0].shape, (1, 42))

    def test_predict_returns_empty_for_unknown_label(self):
        engine = predictor.PredictorEngine(
            model=FakeModel([0.1, 0.2, 0.9]),
            hand_detector=FakeHandDetector([FakeHandLandmarks(build_points())]),
            labels={0: "a", 1: "b"},
        )

        self.assertEqual(engine.predict(self.frame), "")

    def test_get_engine_caches_model_and_hand_detector(self):
        predictor.get_engine.cache_clear()

        with mock.patch.object(predictor, "load_model", return_value=object()) as load_model:
            with mock.patch.object(predictor, "build_hand_detector", return_value=object()) as build_hand_detector:
                first = predictor.get_engine()
                second = predictor.get_engine()

        self.assertIs(first, second)
        load_model.assert_called_once()
        build_hand_detector.assert_called_once()


if __name__ == "__main__":
    unittest.main()
