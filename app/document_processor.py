from pathlib import Path
import hashlib

from parser import DocumentParser
from chunking import DocumentChunker


class DocumentProcessor:

    def __init__(
        self,
        chunk_size=1000,
        chunk_overlap=1
    ):
        self.chunker = DocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    @staticmethod
    def generate_document_id(file_path):
        file_path = Path(file_path)

        return hashlib.sha256(
            str(file_path.resolve()).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def generate_file_hash(file_path):
        sha256 = hashlib.sha256()

        with open(file_path, "rb") as file:
            while True:
                data = file.read(1024 * 1024)

                if not data:
                    break

                sha256.update(data)

        return sha256.hexdigest()

    def process(self, file_path):
        file_path = Path(file_path).resolve()

        filename = file_path.name

        file_hash = self.generate_file_hash(
            file_path
        )

        document_id = self.generate_document_id(
            file_path
        )

        sections = DocumentParser.parse(
            file_path
        )

        all_chunks = []
        global_chunk_index = 0

        for section in sections:
            page_number = section.get(
                "page_number"
            )

            sheet_name = section.get(
                "sheet_name"
            )

            section_chunks = (
                self.chunker.chunk_text(
                    text=section["text"],
                    filename=filename,
                    page_number=page_number,
                    document_id=document_id
                )
            )

            for chunk in section_chunks:
                metadata = chunk["metadata"]

                metadata[
                    "chunk_index"
                ] = global_chunk_index

                metadata[
                    "file_hash"
                ] = file_hash

                metadata[
                    "source_path"
                ] = str(file_path)

                if sheet_name:
                    metadata[
                        "sheet_name"
                    ] = sheet_name

                all_chunks.append(
                    chunk
                )

                global_chunk_index += 1

        return {
            "document_id": document_id,
            "filename": filename,
            "file_hash": file_hash,
            "total_pages": len(sections),
            "total_chunks": len(all_chunks),
            "chunks": all_chunks
        }