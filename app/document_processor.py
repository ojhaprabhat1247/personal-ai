from pathlib import Path
import uuid

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

    def process(self, file_path):

        file_path = Path(file_path)

        document_id = str(uuid.uuid4())
        filename = file_path.name

        pages = DocumentParser.parse(file_path)

        all_chunks = []
        global_chunk_index = 0

        for page in pages:

            page_chunks = self.chunker.chunk_text(
                text=page["text"],
                filename=filename,
                page_number=page["page_number"],
                document_id=document_id
            )

            for chunk in page_chunks:
                chunk["metadata"]["chunk_index"] = global_chunk_index

                all_chunks.append(chunk)

                global_chunk_index += 1

        return {
            "document_id": document_id,
            "filename": filename,
            "total_pages": len(pages),
            "total_chunks": len(all_chunks),
            "chunks": all_chunks
        }