from parser import DocumentParser

print("Parser test started...")

pages = DocumentParser.parse("uploads/sample.pdf")

print("Document parsed successfully!")
print("Total pages extracted:", len(pages))

print("\nFIRST PAGE")
print("=" * 50)

print("Page Number:", pages[0]["page_number"])
print(pages[0]["text"][:1000])