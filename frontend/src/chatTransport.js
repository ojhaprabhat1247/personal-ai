const API_BASE_URL = (
  import.meta.env?.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

async function responseError(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((item) => item.msg).join("; ");
    }
  } catch {
    // A proxy or unavailable server can return a non-JSON error body.
  }
  return `The server could not complete the request (HTTP ${response.status}).`;
}

export async function resetChat({ signal } = {}, fetchRequest = fetch) {
  let response;
  try {
    response = await fetchRequest(`${API_BASE_URL}/chat/reset`, {
      method: "POST",
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error("Unable to reach the backend. Your transcript has been kept.", {
      cause: error,
    });
  }
  if (!response.ok) throw new Error(await responseError(response));
  let confirmation;
  try {
    confirmation = await response.json();
  } catch {
    throw new Error("The server did not confirm the chat reset. Your transcript has been kept.");
  }
  if (confirmation?.status !== "ok") {
    throw new Error("The server did not confirm the chat reset. Your transcript has been kept.");
  }
}

export async function streamChat(
  { message, privacyMode, signal, onDelta, onDone },
  fetchRequest = fetch,
) {
  let response;
  try {
    response = await fetchRequest(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ message, privacy_mode: privacyMode }),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error("Unable to reach the backend. Check that the server is running.", {
      cause: error,
    });
  }

  if (!response.ok) throw new Error(await responseError(response));
  if (!response.headers.get("content-type")?.includes("text/event-stream")) {
    throw new Error("The server returned an unexpected response instead of a chat stream.");
  }
  if (!response.body) throw new Error("The server returned an empty response.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed = false;

  const consumeEvent = (frame) => {
    let event = "message";
    const lines = [];
    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      if (line.startsWith("data:")) lines.push(line.slice(5).replace(/^ /, ""));
    }
    if (!lines.length) return; // Ignore comments/heartbeat frames.
    let data;
    try {
      data = JSON.parse(lines.join("\n"));
    } catch (error) {
      throw new Error("The server sent an invalid chat stream.", { cause: error });
    }
    if (!data || typeof data !== "object") {
      throw new Error("The server sent an invalid chat stream.");
    }
    if (event === "delta") {
      if (typeof data.text !== "string") throw new Error("Invalid chat text received.");
      onDelta(data.text);
    } else if (event === "done") {
      completed = true;
      onDone?.(data);
    } else if (event === "error") {
      throw new Error(data.message || "The response was interrupted.");
    }
  };

  try {
    while (!completed) {
      let part;
      try {
        part = await reader.read();
      } catch (error) {
        if (signal?.aborted) throw error;
        throw new Error("The connection was interrupted. Any text shown is incomplete.", {
          cause: error,
        });
      }
      const { value, done } = part;
      buffer += decoder.decode(value, { stream: !done });
      let boundary;
      while ((boundary = /\r?\n\r?\n/.exec(buffer)) !== null) {
        const frame = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary[0].length);
        consumeEvent(frame);
        if (completed) break;
      }
      if (done) break;
    }
    if (!completed) {
      throw new Error("The connection ended before the response completed. Any text shown is incomplete.");
    }
  } finally {
    try {
      await reader.cancel();
    } catch {
      // Preserve the original stream error if the connection already failed.
    }
    reader.releaseLock();
  }
}
