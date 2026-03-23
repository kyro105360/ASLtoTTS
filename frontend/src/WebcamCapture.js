import React, { useCallback, useEffect, useRef, useState } from "react";
import { applyIncomingCharacter, canCaptureFrame, CAPTURE_INTERVAL_MS, SOCKET_URL } from "./transcript";

const WebcamCapture = ({
  createSocket = (url) => new WebSocket(url),
  getUserMedia = (constraints) => navigator.mediaDevices.getUserMedia(constraints),
  speechSynthesisRef = window.speechSynthesis,
  createUtterance = (text) => new SpeechSynthesisUtterance(text),
}) => {
  const videoRef = useRef(null);
  const webSocketRef = useRef(null);
  const streamRef = useRef(null);

  const [detectedText, setDetectedText] = useState("");
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const [cameraStatus, setCameraStatus] = useState("requesting");
  const [statusMessage, setStatusMessage] = useState("Connecting to the ASL backend...");

  const stopStream = () => {
    if (!streamRef.current) {
      return;
    }

    streamRef.current.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const closeSocket = () => {
    if (!webSocketRef.current) {
      return;
    }

    webSocketRef.current.close();
    webSocketRef.current = null;
  };

  const connectSocket = useCallback(() => {
    setConnectionStatus("connecting");
    setStatusMessage("Connecting to the ASL backend...");

    const socket = createSocket(SOCKET_URL);
    webSocketRef.current = socket;

    socket.onopen = () => {
      if (webSocketRef.current !== socket) {
        return;
      }

      setConnectionStatus("connected");
      setStatusMessage("Streaming live frames to the interpreter.");
    };

    socket.onmessage = (event) => {
      if (webSocketRef.current !== socket) {
        return;
      }

      setDetectedText((current) => applyIncomingCharacter(current, event.data));
    };

    socket.onerror = () => {
      if (webSocketRef.current !== socket) {
        return;
      }

      setConnectionStatus("error");
      setStatusMessage("The backend connection failed. Verify that pythonScripts/main.py is running.");
    };

    socket.onclose = () => {
      if (webSocketRef.current === socket) {
        webSocketRef.current = null;
      }

      setConnectionStatus((current) => (current === "error" ? "error" : "disconnected"));
      setStatusMessage("The backend disconnected. Reconnect after the interpreter is available again.");
    };
  }, [createSocket]);

  useEffect(() => {
    connectSocket();

    if (typeof getUserMedia !== "function") {
      setCameraStatus("unsupported");
      setStatusMessage("This browser does not expose webcam capture APIs.");
      return () => closeSocket();
    }

    getUserMedia({ video: true })
      .then((stream) => {
        streamRef.current = stream;
        setCameraStatus("ready");

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch(() => {
        setCameraStatus("error");
        setStatusMessage("Camera access was denied or is unavailable.");
      });

    return () => {
      stopStream();
      closeSocket();
    };
  }, [connectSocket, getUserMedia]);

  useEffect(() => {
    if (!canCaptureFrame(videoRef.current, webSocketRef.current)) {
      return undefined;
    }

    const intervalId = setInterval(() => {
      captureAndSendFrame();
    }, CAPTURE_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [cameraStatus, connectionStatus]);

  const captureAndSendFrame = () => {
    if (!canCaptureFrame(videoRef.current, webSocketRef.current)) {
      return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob && webSocketRef.current?.readyState === WebSocket.OPEN) {
        webSocketRef.current.send(blob);
      }
    }, "image/jpeg");
  };

  const handleSpeakerClick = () => {
    if (!detectedText.trim()) {
      return;
    }

    speechSynthesisRef.speak(createUtterance(detectedText));
  };

  const handleReconnect = () => {
    closeSocket();
    connectSocket();
  };

  return (
    <section className="captureShell">
      <div className="statusRow">
        <p className={`statusPill statusPill--${connectionStatus}`}>Backend {connectionStatus}</p>
        <p className={`statusPill statusPill--${cameraStatus}`}>Camera {cameraStatus}</p>
      </div>

      <div className="workspace">
        <section className="panel panel--video">
          <div className="panelHeader">
            <p className="eyebrow">Live Signing</p>
            <h2>Webcam feed</h2>
          </div>
          <video ref={videoRef} autoPlay muted playsInline />
          <p className="panelNote">Frames are sent once per second when the camera and websocket are both ready.</p>
        </section>

        <section className="panel panel--transcript">
          <div className="panelHeader">
            <p className="eyebrow">Live Output</p>
            <h2>Transcript</h2>
            <p className="panelNote">{statusMessage}</p>
          </div>

          <textarea
            aria-label="Detected transcript"
            placeholder="Detected text will appear here"
            value={detectedText}
            onChange={(event) => setDetectedText(event.target.value)}
          />

          <div className="actionRow">
            <button type="button" onClick={() => setDetectedText("")}>
              Clear
            </button>
            <button type="button" onClick={handleSpeakerClick} disabled={!detectedText.trim()}>
              Speak
            </button>
            <button type="button" className="buttonSecondary" onClick={handleReconnect}>
              Reconnect
            </button>
          </div>
        </section>
      </div>
    </section>
  );
};

export default WebcamCapture;
