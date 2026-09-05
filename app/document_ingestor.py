from pathlib import Path

from document_processor import DocumentProcessor
from document_store import DocumentStore


class DocumentIngestor:

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".docx",
        ".txt"
    }

    def __init__(self, upload_folder="uploads"):
        self.upload_folder = Path(upload_folder)
        self.processor = DocumentProcessor()
        self.store = DocumentStore()

    def get_supported_files(self):
        if not self.upload_folder.exists():
            return []

        files = []

        for file_path in self.upload_folder.iterdir():
            if (
                file_path.is_file()
                and file_path.suffix.lower()
                in self.SUPPORTED_EXTENSIONS
            ):
                files.append(file_path)

        return sorted(files)

    def ingest_file(self, file_path):
        document = self.processor.process(file_path)

        result = self.store.add_document(document)

        return {
            "filename": document["filename"],
            "status": result["status"],
            "chunks": result["chunks"]
        }

    def ingest_all(self):
        files = self.get_supported_files()

        results = []

        for file_path in files:
            try:
                result = self.ingest_file(file_path)
                results.append(result)

            except Exception as error:
                results.append({
                    "filename": file_path.name,
                    "status": "error",
                    "chunks": 0,
                    "error": str(error)
                })

        return results