import { useState } from "react";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hi! I'm your Personal AI. How can I help you?",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [privacyMode, setPrivacyMode] = useState("auto");

  const sendMessage = async () => {
    const text = input.trim();

    if (!text || loading) return;

    const userMessage = {
      role: "user",
      content: text,
    };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: text,
          privacy_mode: privacyMode,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: data.reply,
          sensitive: data.sensitive,
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            "Unable to reach the Personal AI backend. Please check that the server is running.",
        },
      ]);

      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Personal AI</h1>
          <p>Your private AI workspace</p>
        </div>

        <select
          value={privacyMode}
          onChange={(event) => setPrivacyMode(event.target.value)}
          disabled={loading}
        >
          <option value="auto">Auto</option>
          <option value="privacy_first">Privacy First</option>
          <option value="local_only">Local Only</option>
          <option value="max_quality">Max Quality</option>
        </select>
      </header>

      <main className="chat">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message ${message.role}`}
          >
            <div className="bubble">
              {message.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="bubble">
              Thinking...
            </div>
          </div>
        )}
      </main>

      <footer className="composer">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message Personal AI..."
          rows="1"
          disabled={loading}
        />

        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </footer>
    </div>
  );
}

export default App;