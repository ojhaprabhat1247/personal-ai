import os

from ollama import Client


MODEL = os.getenv("PERSONAL_AI_MODEL", "llama3.2")

# Bound stalled reads, including while cleaning up a disconnected stream.
_client = Client(timeout=120.0)


def generate(messages, stream=False, *, model=None):
    return _client.chat(
        model=model or MODEL,
        messages=messages,
        stream=stream
    )
