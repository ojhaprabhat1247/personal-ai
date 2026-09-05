from pathlib import Path

from pypdf import PdfReader
from docx import Document


class DocumentParser:

    @staticmethod
    def read_pdf(file_path):
        pages = []

        reader = PdfReader(file_path)

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()

            if page_text and page_text.strip():
                pages.append(
                    {
                        "page_number": page_number,
                        "text": page_text.strip()
                    }
                )

        return pages

    @staticmethod
    def read_docx(file_path):
        document = Document(file_path)

        paragraphs = []

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text.strip())

        return [
            {
                "page_number": None,
                "text": "\n".join(paragraphs)
            }
        ]

    @staticmethod
    def read_txt(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()

        return [
            {
                "page_number": None,
                "text": text
            }
        ]

    @staticmethod
    def parse(file_path):
        extension = Path(file_path).suffix.lower()

        if extension == ".pdf":
            return DocumentParser.read_pdf(file_path)

        elif extension == ".docx":
            return DocumentParser.read_docx(file_path)

        elif extension == ".txt":
            return DocumentParser.read_txt(file_path)

        else:
            raise ValueError(
                f"Unsupported file type: {extension}"
            )