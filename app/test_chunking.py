from chunking import DocumentChunker


sample_text = """
Artificial Intelligence systems can process
large amounts of information.

Retrieval Augmented Generation allows an AI
system to retrieve relevant information before
generating an answer.

This improves factual accuracy and allows the
model to work with external knowledge.
"""


chunker = DocumentChunker(
    chunk_size=100,
    chunk_overlap=1
)


chunks = chunker.chunk_text(
    text=sample_text,
    filename="test_document.txt",
    page_number=1,
    document_id="doc-001"
)


for chunk in chunks:

    print("=" * 50)

    print("TEXT:")
    print(chunk["text"])

    print("\nMETADATA:")
    print(chunk["metadata"])