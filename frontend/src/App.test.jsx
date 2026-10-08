import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "./App.jsx";

let container;
let root;
let fetchMock;

const frame = (event, data) => new TextEncoder().encode(
  `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`,
);
const completedReply = () => new Response(new ReadableStream({
  start(controller) {
    controller.enqueue(frame("delta", { text: "Previous answer" }));
    controller.enqueue(frame("done", { privacy_mode: "auto", sensitive: false }));
    controller.close();
  },
}), { headers: { "Content-Type": "text/event-stream" } });

beforeEach(async () => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock); // No test request can reach a real backend.
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  await act(async () => { root.render(<App />); });
});

afterEach(async () => {
  await act(async () => { root.unmount(); });
  container.remove();
  vi.unstubAllGlobals();
});

async function typeMessage(value) {
  await act(async () => {
    const textarea = container.querySelector("textarea");
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(textarea, value);
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function sendMessage(value = "Previous question") {
  await typeMessage(value);
  await act(async () => {
    container.querySelector("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
}

test("New Chat keeps the transcript pending, then restores the greeting after backend confirmation", async () => {
  fetchMock.mockResolvedValueOnce(completedReply());
  await sendMessage();
  await typeMessage("Unsent draft");
  const policy = container.querySelector("select");
  await act(async () => {
    policy.value = "local_only";
    policy.dispatchEvent(new Event("change", { bubbles: true }));
  });
  let finishReset;
  fetchMock.mockImplementationOnce(() => new Promise((resolve) => { finishReset = resolve; }));
  await act(async () => { container.querySelector(".new-chat-button").click(); });

  expect(container.textContent).toContain("Previous question");
  expect(container.textContent).toContain("Previous answer");
  expect(container.querySelector(".new-chat-button").disabled).toBe(true);
  expect(container.querySelector("textarea").disabled).toBe(true);
  expect(fetchMock.mock.lastCall[0]).toMatch(/\/chat\/reset$/);
  expect(fetchMock.mock.lastCall[1].method).toBe("POST");

  await act(async () => { finishReset(Response.json({ status: "ok" })); });
  expect(container.querySelectorAll("article")).toHaveLength(1);
  expect(container.querySelector("article").textContent).toContain("Hi! I'm your Personal AI.");
  expect(container.textContent).not.toContain("Previous answer");
  expect(container.querySelector("textarea").value).toBe("");
  expect(container.querySelector("select").value).toBe("local_only");
  expect(container.querySelector(".new-chat-button").disabled).toBe(false);
  expect(container.querySelector('[role="alert"]')).toBeNull();
});

test("failed New Chat preserves transcript and draft and displays the backend error", async () => {
  fetchMock.mockResolvedValueOnce(completedReply());
  await sendMessage();
  await typeMessage("Keep this draft");
  fetchMock.mockResolvedValueOnce(Response.json(
    { detail: "Unable to start a new chat. Your conversation has been kept." }, { status: 500 },
  ));
  await act(async () => { container.querySelector(".new-chat-button").click(); });

  expect(container.querySelectorAll("article")).toHaveLength(3);
  expect(container.textContent).toContain("Previous question");
  expect(container.textContent).toContain("Previous answer");
  expect(container.querySelector("textarea").value).toBe("Keep this draft");
  expect(container.querySelector('[role="alert"]').textContent).toContain("conversation has been kept");
  expect(container.querySelector(".new-chat-button").disabled).toBe(false);
});

test("New Chat is disabled during streaming and partial output updates incrementally", async () => {
  let source;
  fetchMock.mockResolvedValueOnce(new Response(new ReadableStream({
    start(controller) { source = controller; },
  }), { headers: { "Content-Type": "text/event-stream" } }));
  await sendMessage();
  await act(async () => { source.enqueue(frame("delta", { text: "First part" })); });
  expect(container.textContent).toContain("First part");
  expect(container.querySelector(".new-chat-button").disabled).toBe(true);
  await act(async () => { container.querySelector(".new-chat-button").click(); });
  expect(fetchMock).toHaveBeenCalledTimes(1);
  await act(async () => {
    source.enqueue(frame("delta", { text: " and second part" }));
    source.enqueue(frame("done", { privacy_mode: "auto", sensitive: false }));
    source.close();
  });
  expect(container.textContent).toContain("First part and second part");
  expect(container.querySelector(".new-chat-button").disabled).toBe(false);
});

test("Enter sends multiline text while Shift+Enter and IME composition do not send", async () => {
  await typeMessage("First line\nSecond line");
  const textarea = container.querySelector("textarea");
  for (const properties of [{ shiftKey: true }, { isComposing: true }]) {
    const key = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true, ...properties });
    await act(async () => { textarea.dispatchEvent(key); });
    expect(key.defaultPrevented).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  }
  fetchMock.mockResolvedValueOnce(completedReply());
  const enter = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
  await act(async () => { textarea.dispatchEvent(enter); });
  expect(enter.defaultPrevented).toBe(true);
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(JSON.parse(fetchMock.mock.lastCall[1].body).message).toBe("First line\nSecond line");
});
