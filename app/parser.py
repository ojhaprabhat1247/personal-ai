from pathlib import Path

from pypdf import PdfReader
from docx import Document


class DocumentParser:

    @staticmethod
    def read_pdf(file_path):
        text = ""

        reader = PdfReader(file_path)

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

        return text.strip()

    @staticmethod
    def read_docx(file_path):
        document = Document(file_path)

        paragraphs = []

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text)

        return "\n".join(paragraphs)

    @staticmethod
    def read_txt(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

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