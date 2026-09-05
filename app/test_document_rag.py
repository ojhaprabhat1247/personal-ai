from document_rag import DocumentRAG


rag = DocumentRAG(
    n_results=5
)

question = (
    "What subnet mask is used when "
    "the company needs six subnets?"
)

print("QUESTION:")
print(question)

print("\nSearching documents and generating answer...\n")

result = rag.ask(question)

print("ANSWER:")
print(result["answer"])

print("\nSOURCES:")

for source in result["sources"]:
    print(
        f'- {source["filename"]} '
        f'- Page {source["page_number"]}'
    )