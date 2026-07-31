from ollama import embeddings

MODEL = "nomic-embed-text"


def generate_embedding(text):

    response = embeddings(
        model=MODEL,
        prompt=text
    )

    return response["embedding"]