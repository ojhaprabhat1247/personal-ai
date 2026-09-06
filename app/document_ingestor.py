from pathlib import Path

from document_processor import DocumentProcessor
from document_store import DocumentStore
from folder_config import FolderConfig


class DocumentIngestor:

    SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".xlsx",
    ".csv"
     }

    def __init__(self):
        self.processor = DocumentProcessor()
        self.store = DocumentStore()

        self.folder_config = FolderConfig()

        self.approved_folders = (
            self.folder_config.load_approved_folders()
        )

    def get_supported_files(self):
        files = []

        for folder in self.approved_folders:
            for file_path in folder.rglob("*"):
                if (
                    file_path.is_file()
                    and file_path.suffix.lower()
                    in self.SUPPORTED_EXTENSIONS
                ):
                    files.append(file_path)

        return sorted(files)

    def ingest_file(self, file_path):
        file_path = Path(file_path).resolve()

        if not self.is_file_approved(file_path):
            raise PermissionError(
                f"File is outside approved folders: {file_path}"
            )

        document = self.processor.process(file_path)

        result = self.store.add_document(document)

        return {
            "filename": document["filename"],
            "status": result["status"],
            "chunks": result["chunks"]
        }

    def is_file_approved(self, file_path):
        file_path = Path(file_path).resolve()

        for folder in self.approved_folders:
            try:
                file_path.relative_to(folder)
                return True
            except ValueError:
                continue

        return False

    def remove_stale_documents(self):
        indexed_documents = (
            self.store.get_all_documents()
        )

        removed = []

        for document_id, source_path in (
            indexed_documents.items()
        ):
            file_path = Path(source_path)

            if not file_path.exists():
                self.store.delete_document(
                    document_id
                )

                removed.append(source_path)
                continue

            if not self.is_file_approved(file_path):
                self.store.delete_document(
                    document_id
                )

                removed.append(source_path)

        return removed

    def ingest_all(self):
        self.remove_stale_documents()

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