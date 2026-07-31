import uuid
import chromadb
import embeddings
from datetime import datetime

client = chromadb.PersistentClient(path="data/chroma")

collection = client.get_or_create_collection(
    name="memory"
)


def add_memory(
    text,
    category="general",
    source="chat",
    importance=1
):

    vector = embeddings.generate_embedding(text)

    collection.add(
        ids=[str(uuid.uuid4())],

        documents=[text],

        embeddings=[vector],

        metadatas=[
            {
                "category": category,
                "source": source,
                "importance": importance,
                "created_at": datetime.now().isoformat()
            }
        ]
    )


def search_memory(query, n_results=5):

    vector = embeddings.generate_embedding(query)

    results = collection.query(
        query_embeddings=[vector],
        n_results=n_results
    )

    memories = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for i in range(len(documents)):

        memories.append(
            {
                "text": documents[i],
                "metadata": metadatas[i] if metadatas else {},
                "score": distances[i] if distances else None
            }
        )

    return memories


def clear_memory():

    global collection

    client.delete_collection("memory")

    collection = client.get_or_create_collection(
        name="memory"
    )
    
#tempory for check
def show_all():

    data = collection.get()

    print(data)