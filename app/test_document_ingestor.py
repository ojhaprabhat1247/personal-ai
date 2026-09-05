from document_ingestor import DocumentIngestor


ingestor = DocumentIngestor()

print("Starting document ingestion...\n")

results = ingestor.ingest_all()

if not results:
    print("No supported documents found.")

else:
    for result in results:
        print(f"File: {result['filename']}")
        print(f"Status: {result['status']}")
        print(f"Chunks Added: {result['chunks']}")

        if result["status"] == "error":
            print(f"Error: {result['error']}")

        print("-" * 40)

print(
    f"\nTotal document chunks in DB: "
    f"{ingestor.store.count()}"
)