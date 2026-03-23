import argparse
import asyncio
import time

import cv2
import numpy as np
import websockets


def backend_candidates():
    candidates = [("default", None)]

    if hasattr(cv2, "CAP_DSHOW"):
        candidates.append(("dshow", cv2.CAP_DSHOW))

    if hasattr(cv2, "CAP_MSMF"):
        candidates.append(("msmf", cv2.CAP_MSMF))

    return candidates


def try_open_camera(index):
    for backend_name, backend_flag in backend_candidates():
        capture = cv2.VideoCapture(index) if backend_flag is None else cv2.VideoCapture(index, backend_flag)
        if not capture.isOpened():
            capture.release()
            continue

        ok, frame = capture.read()
        if ok and frame is not None:
            return capture, backend_name

        capture.release()

    return None, None


def find_available_cameras(max_index):
    available = []
    for index in range(max_index + 1):
        capture, backend_name = try_open_camera(index)
        if capture is None:
            continue

        available.append((index, backend_name))
        capture.release()

    return available


def open_camera(camera_index, max_index):
    if camera_index == "auto":
        available = find_available_cameras(max_index)
        if not available:
            raise RuntimeError(
                "No webcam could be opened. Check camera permissions and close any app that may be using the webcam."
            )

        selected_index, _ = available[0]
        capture, backend_name = try_open_camera(selected_index)
        return capture, selected_index, backend_name

    capture, backend_name = try_open_camera(camera_index)
    if capture is None:
        available = find_available_cameras(max_index)
        available_text = ", ".join(f"{index} ({backend})" for index, backend in available) or "none"
        raise RuntimeError(
            f"Unable to open webcam at index {camera_index}. Available camera slots detected: {available_text}."
        )

    return capture, camera_index, backend_name


def update_text(buffer, character):
    if character == "\b":
        return buffer[:-1]

    if character == "C":
        return ""

    return buffer + character


def build_preview(frame, character, transcript):
    preview = frame.copy()
    current_prediction = character if character else "-"
    transcript_tail = transcript[-32:] or "(empty)"

    cv2.rectangle(preview, (18, 18), (620, 132), (10, 16, 32), -1)
    cv2.rectangle(preview, (18, 18), (620, 132), (125, 211, 252), 2)
    cv2.putText(preview, "ASL Interpreter", (34, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (238, 242, 255), 2)
    cv2.putText(preview, f"Current sign: {current_prediction}", (34, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (125, 211, 252), 2)
    cv2.putText(preview, f"Output: {transcript_tail}", (34, 114), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (245, 158, 11), 2)
    return preview


def run_console(camera_index, max_index):
    import predictor

    capture, active_index, backend_name = open_camera(camera_index, max_index)

    print("Console ASL interpreter started.")
    print(f"Using webcam index {active_index} via {backend_name}.")
    print("Make a sign in front of the webcam. Press Q in the preview window to stop.")

    transcript = ""
    last_character = ""
    blank_frames = 0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError("Failed to read a frame from the webcam.")

            frame = cv2.flip(frame, 1)
            character = predictor.runCamera(frame)

            if not character:
                blank_frames += 1
                if blank_frames >= 8:
                    last_character = ""
            else:
                blank_frames = 0
                if character != last_character:
                    transcript = update_text(transcript, character)
                    last_character = character
                    print(f"[{time.strftime('%H:%M:%S')}] {character!r} -> {transcript or '(empty)'}")

            preview = build_preview(frame, character, transcript)
            cv2.imshow("ASL Interpreter", preview)

            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


async def echo(websocket, path=None):
    import predictor

    async for message in websocket:
        nparr = np.frombuffer(message, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        character = predictor.runCamera(frame)
        if character:
            print(f"Received character: {character}")
        await websocket.send(character)


async def run_websocket_server():
    async with websockets.serve(echo, "localhost", 4000):
        print("WebSocket server started on ws://localhost:4000")
        await asyncio.Future()


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("console", "websocket"),
        default="console",
        help="Run the interpreter from a local webcam or as a websocket server.",
    )
    parser.add_argument(
        "--camera-index",
        default="auto",
        help="Webcam index to open in console mode, or 'auto' to probe available cameras.",
    )
    parser.add_argument(
        "--max-camera-index",
        type=int,
        default=5,
        help="Highest camera index to probe when using auto-detection or listing cameras.",
    )
    parser.add_argument(
        "--list-cameras",
        action="store_true",
        help="List camera indices that OpenCV can open, then exit.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    if args.list_cameras:
        cameras = find_available_cameras(args.max_camera_index)
        if not cameras:
            print("No cameras detected by OpenCV.")
        else:
            for index, backend_name in cameras:
                print(f"Camera {index} via {backend_name}")
    elif args.mode == "websocket":
        asyncio.run(run_websocket_server())
    else:
        run_console(
            camera_index=args.camera_index if args.camera_index == "auto" else int(args.camera_index),
            max_index=args.max_camera_index,
        )
