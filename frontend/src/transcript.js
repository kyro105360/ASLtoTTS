export const CAPTURE_INTERVAL_MS = 1000;
export const SOCKET_URL = "ws://localhost:4000";

export function applyIncomingCharacter(currentText, incomingCharacter) {
  if (!incomingCharacter) {
    return currentText;
  }

  if (incomingCharacter === "\b") {
    return currentText.slice(0, -1);
  }

  if (incomingCharacter === "C") {
    return "";
  }

  return `${currentText}${incomingCharacter}`;
}

export function canCaptureFrame(video, socket) {
  return Boolean(
    video &&
      socket &&
      socket.readyState === WebSocket.OPEN &&
      video.videoWidth >= 640 &&
      video.videoHeight >= 480
  );
}
