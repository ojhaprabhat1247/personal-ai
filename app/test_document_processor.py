from document_processor import DocumentProcessor


processor = DocumentProcessor(
    chunk_size=1000,
    chunk_overlap=1
)

document = processor.process(
    "uploads/sample.pdf"
)

print("Document processed successfully!")
print("Document ID:", document["document_id"])
print("Filename:", document["filename"])
print("Total Pages:", document["total_pages"])
print("Total Chunks:", document["total_chunks"])


print("\nFIRST 3 CHUNKS")
print("=" * 60)

for chunk in document["chunks"][:3]:

    print("\nTEXT:")
    print(chunk["text"][:300])

    print("\nMETADATA:")
    print(chunk["metadata"])

    print("-" * 60)