from ollama import chat


MODEL = "llama3.2"


def generate(messages, stream=False):

    return chat(
        model=MODEL,
        messages=messages,
        stream=stream
    )