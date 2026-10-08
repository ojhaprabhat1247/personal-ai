import { useEffect, useRef, useState } from "react";
import { resetChat, streamChat } from "./chatTransport";
import "./App.css";

const initialMessages = () => [{
  id: "welcome",
  role: "assistant",
  content: "Hi! I'm your Personal AI. How can I help you?",
  status: "complete",
}];

function App() {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [phase, setPhase] = useState("idle");
  const [error, setError] = useState("");
  const [privacyMode, setPrivacyMode] = useState("auto");
  const chatRef = useRef(null);
  const inputRef = useRef(null);
  const requestRef = useRef(null);
  const composingRef = useRef(false);
  const followLatestRef = useRef(true);
  const pending = phase !== "idle";

  useEffect(() => () => requestRef.current?.abort(), []);

  useEffect(() => {
    const chat = chatRef.current;
    if (chat && followLatestRef.current) chat.scrollTop = chat.scrollHeight;
  }, [messages, phase, error]);

  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
    }
  }, [input]);

  useEffect(() => {
    if (!pending) inputRef.current?.focus();
  }, [pending]);

  const startNewChat = async () => {
    if (requestRef.current) return;
    const controller = new AbortController();
    requestRef.current = controller;
    setError("");
    setPhase("resetting");
    try {
      await resetChat({ signal: controller.signal });
      if (!controller.signal.aborted) {
        followLatestRef.current = true;
        setMessages(initialMessages());
        setInput("");
      }
    } catch (resetError) {
      if (!controller.signal.aborted) {
        setError(resetError.message || "Unable to start a new chat. Your transcript has been kept.");
      }
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
        if (!controller.signal.aborted) setPhase("idle");
      }
    }
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || requestRef.current) return;

    const controller = new AbortController();
    requestRef.current = controller;
    const assistantId = crypto.randomUUID();
    followLatestRef.current = true;
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content: text, status: "complete" },
      { id: assistantId, role: "assistant", content: "", status: "pending" },
    ]);
    setInput("");
    setError("");
    setPhase("waiting");

    const updateAssistant = (update) => {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId ? update(message) : message,
        ),
      );
    };

    try {
      await streamChat({
        message: text,
        privacyMode,
        signal: controller.signal,
        onDelta: (delta) => {
          if (controller.signal.aborted) return;
          setPhase("streaming");
          updateAssistant((message) => ({
            ...message,
            content: message.content + delta,
            status: "streaming",
          }));
        },
        onDone: (metadata) => {
          if (controller.signal.aborted) return;
          updateAssistant((message) => ({
            ...message,
            status: "complete",
            sensitive: metadata.sensitive,
          }));
        },
      });
    } catch (requestError) {
      if (!controller.signal.aborted) {
        updateAssistant((message) => ({ ...message, status: "error" }));
        setError(requestError.message || "The response could not be completed.");
      }
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
        if (!controller.signal.aborted) setPhase("idle");
      }
    }
  };

  const handleKeyDown = (event) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing &&
      !composingRef.current &&
      event.keyCode !== 229
    ) {
      event.preventDefault();
      void sendMessage();
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">P</span>
          <div>
            <h1>Personal AI</h1>
            <p>Your private AI workspace</p>
          </div>
        </div>
        <div className="header-actions">
          <button
            type="button"
            className="new-chat-button"
            onClick={() => { void startNewChat(); }}
            disabled={pending}
            title="Start a new conversation. Saved memories and profile are kept."
          >
            {phase === "resetting" ? "Starting…" : "New Chat"}
          </button>
          <div className="privacy-control">
            <label htmlFor="privacy-mode">Privacy policy</label>
            <select
              id="privacy-mode"
              value={privacyMode}
              onChange={(event) => setPrivacyMode(event.target.value)}
              disabled={pending}
            >
              <option value="auto">Auto</option>
              <option value="privacy_first">Privacy First</option>
              <option value="local_only">Local Only</option>
              <option value="max_quality">Max Quality</option>
            </select>
          </div>
        </div>
      </header>

      <main
        className="chat"
        ref={chatRef}
        aria-label="Conversation"
        tabIndex={0}
        onScroll={(event) => {
          const { scrollHeight, scrollTop, clientHeight } = event.currentTarget;
          followLatestRef.current = scrollHeight - scrollTop - clientHeight < 80;
        }}
      >
        <div className="messages">
          {messages.map((message) => (
            <article
              key={message.id}
              className={`message ${message.role}`}
              aria-label={message.role === "user" ? "Your message" : "Personal AI response"}
            >
              <span className="message-label">
                {message.role === "user" ? "You" : "Personal AI"}
              </span>
              <div className={`bubble ${message.status === "error" ? "interrupted" : ""}`}>
                {message.content || (
                  <span className="placeholder">
                    {message.status === "error" ? "No response received." : "Thinking…"}
                  </span>
                )}
                {message.status === "streaming" && (
                  <span className="stream-cursor" aria-hidden="true" />
                )}
              </div>
              {message.status === "error" && message.content && (
                <span className="incomplete-label">Response incomplete</span>
              )}
            </article>
          ))}
        </div>
      </main>

      <footer className="composer-area">
        {error && <div className="request-error" role="alert">{error}</div>}
        <div className="generation-status" role="status" aria-live="polite" aria-atomic="true">
          {phase === "resetting" && "Starting a new chat…"}
          {phase === "waiting" && "Preparing your response…"}
          {phase === "streaming" && "Responding…"}
          {phase === "idle" && messages.length > 1 && !error && "Response complete."}
        </div>
        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            void sendMessage();
          }}
        >
          <label className="sr-only" htmlFor="chat-input">Message Personal AI</label>
          <textarea
            id="chat-input"
            ref={inputRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => { composingRef.current = true; }}
            onCompositionEnd={() => { composingRef.current = false; }}
            placeholder="Message Personal AI…"
            rows={1}
            disabled={pending}
            aria-describedby="composer-hint"
          />
          <button type="submit" disabled={pending || !input.trim()}>
            {pending && phase !== "resetting" ? "Sending…" : "Send"}
          </button>
        </form>
        <p className="composer-hint" id="composer-hint">
          Enter to send <span aria-hidden="true">·</span> Shift + Enter for a new line
        </p>
      </footer>
    </div>
  );
}

export default App;
