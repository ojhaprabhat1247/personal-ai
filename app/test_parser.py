from parser import DocumentParser

print("Parser test started...")

text = DocumentParser.parse("uploads/sample.pdf")

print("Document parsed successfully!")
print(text[:1000])