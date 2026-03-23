import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pythonScripts"))

import main


class FakeCapture:
    def __init__(self, opened, frame):
        self.opened = opened
        self.frame = frame
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        return self.frame is not None, self.frame

    def release(self):
        self.released = True


class CameraMainTests(unittest.TestCase):
    def test_update_text_handles_backspace_and_clear(self):
        self.assertEqual(main.update_text("abc", "\b"), "ab")
        self.assertEqual(main.update_text("abc", "C"), "")
        self.assertEqual(main.update_text("ab", "c"), "abc")

    def test_parse_args_supports_console_camera_options(self):
        args = main.parse_args(["--mode", "console", "--camera-index", "2", "--max-camera-index", "9"])

        self.assertEqual(args.mode, "console")
        self.assertEqual(args.camera_index, "2")
        self.assertEqual(args.max_camera_index, 9)

    def test_find_available_cameras_collects_successful_indices(self):
        first = FakeCapture(True, object())
        third = FakeCapture(True, object())

        with mock.patch.object(main, "try_open_camera", side_effect=[(first, "default"), (None, None), (third, "msmf")]):
            cameras = main.find_available_cameras(2)

        self.assertEqual(cameras, [(0, "default"), (2, "msmf")])
        self.assertTrue(first.released)
        self.assertTrue(third.released)

    def test_open_camera_auto_uses_first_available_camera(self):
        capture = FakeCapture(True, object())

        with mock.patch.object(main, "find_available_cameras", return_value=[(1, "msmf"), (3, "dshow")]):
            with mock.patch.object(main, "try_open_camera", return_value=(capture, "msmf")) as try_open_camera:
                selected_capture, index, backend = main.open_camera("auto", 5)

        self.assertIs(selected_capture, capture)
        self.assertEqual(index, 1)
        self.assertEqual(backend, "msmf")
        try_open_camera.assert_called_once_with(1)

    def test_open_camera_includes_available_slots_in_error_message(self):
        with mock.patch.object(main, "try_open_camera", return_value=(None, None)):
            with mock.patch.object(main, "find_available_cameras", return_value=[(1, "default"), (4, "msmf")]):
                with self.assertRaisesRegex(RuntimeError, "1 \\(default\\), 4 \\(msmf\\)"):
                    main.open_camera(2, 5)

    def test_try_open_camera_tries_available_backends_until_one_reads_a_frame(self):
        attempts = []
        captures = {
            ("default", None): FakeCapture(False, None),
            ("dshow", 100): FakeCapture(True, None),
            ("msmf", 200): FakeCapture(True, object()),
        }

        def fake_video_capture(index, backend=None):
            name = "default" if backend is None else "dshow" if backend == 100 else "msmf"
            attempts.append((index, name))
            return captures[(name, backend)]

        with mock.patch.object(main, "backend_candidates", return_value=[("default", None), ("dshow", 100), ("msmf", 200)]):
            with mock.patch.object(main.cv2, "VideoCapture", side_effect=fake_video_capture):
                capture, backend_name = main.try_open_camera(3)

        self.assertIs(capture, captures[("msmf", 200)])
        self.assertEqual(backend_name, "msmf")
        self.assertEqual(attempts, [(3, "default"), (3, "dshow"), (3, "msmf")])
        self.assertTrue(captures[("default", None)].released)
        self.assertTrue(captures[("dshow", 100)].released)


if __name__ == "__main__":
    unittest.main()
