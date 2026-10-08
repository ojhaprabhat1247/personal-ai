import assert from "node:assert/strict";
import test from "node:test";
import { resetChat, streamChat } from "./chatTransport.js";

const encode = (text) => new TextEncoder().encode(text);
const event = (kind, data) => `event: ${kind}\r\ndata: ${JSON.stringify(data)}\r\n\r\n`;

test("New Chat posts a reset and requires explicit backend confirmation", async () => {
  const signal = new AbortController().signal;
  await resetChat({ signal }, async (url, options) => {
    assert.ok(url.endsWith("/chat/reset"));
    assert.equal(options.method, "POST");
    assert.equal(options.signal, signal);
    return Response.json({ status: "ok" });
  });
  for (const response of [Response.json({ status: "failed" }), new Response("not JSON")]) {
    await assert.rejects(resetChat({}, async () => response), /did not confirm the chat reset/);
  }
  await assert.rejects(resetChat({}, async () => Response.json(
    { detail: "Unable to start a new chat." }, { status: 500 },
  )), /Unable to start a new chat/);
});

function fakeResponse(parts) {
  return new Response(new ReadableStream({
    start(controller) {
      for (const part of parts) controller.enqueue(part);
      controller.close();
    },
  }), { headers: { "Content-Type": "text/event-stream" } });
}

test("streams Unicode across byte/frame boundaries and sends the existing policy values", async () => {
  const metadata = { privacy_mode: "privacy_first", sensitive: false, sensitivity_reasons: [] };
  const bytes = encode(event("delta", { text: "नमस्ते\n" }) +
    event("delta", { text: "world" }) + event("done", metadata));
  const pieces = Array.from(bytes, (byte) => Uint8Array.of(byte));
  const received = [];
  let completed;
  await streamChat({
    message: "Hello", privacyMode: "privacy_first",
    onDelta: (text) => received.push(text), onDone: (data) => { completed = data; },
  }, async (url, options) => {
    assert.ok(url.endsWith("/chat/stream"));
    assert.deepEqual(JSON.parse(options.body), { message: "Hello", privacy_mode: "privacy_first" });
    return fakeResponse(pieces);
  });
  assert.deepEqual(received, ["नमस्ते\n", "world"]);
  assert.deepEqual(completed, metadata);
});

test("keeps partial text and rejects an error event without completing", async () => {
  const received = [];
  let completed = false;
  await assert.rejects(streamChat({
    message: "Hi", privacyMode: "auto", onDelta: (text) => received.push(text),
    onDone: () => { completed = true; },
  }, async () => fakeResponse([encode(event("delta", { text: "Partial" }) +
    event("error", { message: "Provider unavailable" }))])), /Provider unavailable/);
  assert.deepEqual(received, ["Partial"]);
  assert.equal(completed, false);
});

test("rejects truncated streams, including a truncated terminal frame", async () => {
  for (const suffix of ["", 'event: done\ndata: {"sensitive":false}']) {
    await assert.rejects(streamChat({
      message: "Hi", privacyMode: "auto", onDelta() {},
    }, async () => fakeResponse([encode(event("delta", { text: "Partial" }) + suffix)])),
    /before the response completed/);
  }
});

test("distinguishes server validation errors from connection errors", async () => {
  const request = { message: "Hi", privacyMode: "auto", onDelta() {} };
  await assert.rejects(streamChat(request, async () => new Response(
    JSON.stringify({ detail: "Message cannot be empty." }), { status: 400 },
  )), /Message cannot be empty/);
  await assert.rejects(streamChat(request, async () => {
    throw new TypeError("Failed to fetch");
  }), /Unable to reach the backend/);
});

test("rejects an unexpected non-streaming response", async () => {
  await assert.rejects(streamChat({
    message: "Hi", privacyMode: "auto", onDelta() {},
  }, async () => new Response('{"reply":"Hi"}', {
    headers: { "Content-Type": "application/json" },
  })), /unexpected response/);
});

test("delivers the first delta before completion and reports a later connection failure", async () => {
  const received = [];
  let source;
  const response = new Response(new ReadableStream({
    start(controller) {
      source = controller;
      controller.enqueue(encode(event("delta", { text: "Visible now" })));
    },
  }), { headers: { "Content-Type": "text/event-stream" } });
  await assert.rejects(streamChat({
    message: "Hi", privacyMode: "auto",
    onDelta(text) {
      received.push(text);
      // The producer has not completed; the first text must already be visible.
      source.error(new TypeError("network terminated"));
    },
  }, async () => response), /connection was interrupted/);
  assert.deepEqual(received, ["Visible now"]);
});
