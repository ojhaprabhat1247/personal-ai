from document_processor import DocumentProcessor
from document_store import DocumentStore


print("Processing document...")

processor = DocumentProcessor(
    chunk_size=1000,
    chunk_overlap=1
)

document = processor.process(
    "uploads/sample.pdf"
)

print(
    "Document processed:",
    document["total_chunks"],
    "chunks"
)


print("\nStoring document in ChromaDB...")

store = DocumentStore()

result = store.add_document(document)

print("Index Status:", result["status"])
print("Chunks Added:", result["chunks"])
print(
    "Total document chunks in DB:",
    store.count()
)
print("Total document chunks in DB:", store.count())


print("\nSearching document...")

query = "What is the router configuration?"

results = store.search(
    query,
    n_results=3
)


for index, result in enumerate(results, start=1):

    print("\n" + "=" * 60)
    print("RESULT:", index)

    print("\nTEXT:")
    print(result["text"][:500])

    print("\nSOURCE:")
    print(
        result["metadata"].get("filename"),
        "- Page",
        result["metadata"].get("page_number")
    )

    print("DISTANCE:", result["distance"])