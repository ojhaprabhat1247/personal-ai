import chromadb


client = chromadb.PersistentClient(
    path="data/chroma"
)

try:
    client.delete_collection("documents")
    print("Old documents collection deleted.")
except Exception:
    print("Documents collection did not exist.")

client.get_or_create_collection(
    name="documents"
)

print("Fresh documents collection created.")