import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import WebcamCapture from "./WebcamCapture";

class FakeSocket {
  constructor() {
    this.readyState = WebSocket.CONNECTING;
    this.send = jest.fn();
    this.close = jest.fn(() => {
      this.readyState = WebSocket.CLOSED;
      if (this.onclose) {
        this.onclose();
      }
    });
  }

  open() {
    this.readyState = WebSocket.OPEN;
    this.onopen?.();
  }

  message(data) {
    this.onmessage?.({ data });
  }
}

describe("WebcamCapture", () => {
  beforeAll(() => {
    global.WebSocket = { OPEN: 1, CONNECTING: 0, CLOSED: 3 };
  });

  beforeEach(() => {
    jest.useFakeTimers();
    HTMLCanvasElement.prototype.getContext = jest.fn(() => ({ drawImage: jest.fn() }));
    HTMLCanvasElement.prototype.toBlob = jest.fn((callback) => callback(new Blob(["frame"], { type: "image/jpeg" })));
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.clearAllTimers();
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  test("shows backend status and applies incoming transcript updates", async () => {
    const socket = new FakeSocket();
    const track = { stop: jest.fn() };
    const getUserMedia = jest.fn().mockResolvedValue({ getTracks: () => [track] });
    const speechSynthesisRef = { speak: jest.fn() };

    render(
      <WebcamCapture
        createSocket={() => socket}
        getUserMedia={getUserMedia}
        speechSynthesisRef={speechSynthesisRef}
        createUtterance={(text) => ({ text })}
      />
    );

    await waitFor(() => expect(getUserMedia).toHaveBeenCalled());

    act(() => {
      socket.open();
      socket.message("a");
      socket.message("b");
      socket.message("\b");
    });

    expect(screen.getByText("Backend connected")).toBeInTheDocument();
    expect(screen.getByLabelText("Detected transcript")).toHaveValue("a");

    fireEvent.click(screen.getByText("Speak"));
    expect(speechSynthesisRef.speak).toHaveBeenCalledWith({ text: "a" });

    fireEvent.click(screen.getByText("Clear"));
    expect(screen.getByLabelText("Detected transcript")).toHaveValue("");
  });

  test("sends one frame per interval without multiplying timers on rerender", async () => {
    const socket = new FakeSocket();
    const getUserMedia = jest.fn().mockResolvedValue({ getTracks: () => [{ stop: jest.fn() }] });

    const { container } = render(
      <WebcamCapture createSocket={() => socket} getUserMedia={getUserMedia} speechSynthesisRef={{ speak: jest.fn() }} />
    );

    const video = container.querySelector("video");
    Object.defineProperty(video, "videoWidth", { configurable: true, value: 800 });
    Object.defineProperty(video, "videoHeight", { configurable: true, value: 600 });

    await waitFor(() => expect(getUserMedia).toHaveBeenCalled());

    act(() => {
      socket.open();
    });

    act(() => {
      jest.advanceTimersByTime(3000);
    });

    expect(socket.send).toHaveBeenCalledTimes(3);

    act(() => {
      socket.message("a");
      jest.advanceTimersByTime(2000);
    });

    expect(socket.send).toHaveBeenCalledTimes(5);
  });
});
