import { applyIncomingCharacter, canCaptureFrame } from "./transcript";

describe("transcript utilities", () => {
  test("applies normal characters and spaces", () => {
    expect(applyIncomingCharacter("ab", "c")).toBe("abc");
    expect(applyIncomingCharacter("abc", " ")).toBe("abc ");
  });

  test("supports backspace and clear control characters", () => {
    expect(applyIncomingCharacter("abc", "\b")).toBe("ab");
    expect(applyIncomingCharacter("abc", "C")).toBe("");
  });

  test("ignores empty payloads", () => {
    expect(applyIncomingCharacter("abc", "")).toBe("abc");
  });

  test("requires an open socket and large enough frame before capture", () => {
    const socket = { readyState: WebSocket.OPEN };
    const video = { videoWidth: 640, videoHeight: 480 };

    expect(canCaptureFrame(video, socket)).toBe(true);
    expect(canCaptureFrame({ videoWidth: 320, videoHeight: 240 }, socket)).toBe(false);
    expect(canCaptureFrame(video, { readyState: WebSocket.CONNECTING })).toBe(false);
  });
});
