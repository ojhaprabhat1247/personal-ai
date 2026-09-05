import re
from typing import List, Dict


class DocumentChunker:

    def __init__(
        self,
        chunk_size=1000,
        chunk_overlap=1
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_sentences(self, text: str) -> List[str]:
        sentences = re.split(
            r'(?<=[.!?])\s+',
            text.strip()
        )

        return [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

    def chunk_text(
        self,
        text: str,
        filename: str,
        page_number=None,
        document_id=None
    ) -> List[Dict]:

        sentences = self.split_sentences(text)

        chunks = []
        current_sentences = []
        chunk_index = 0

        for sentence in sentences:

            candidate_sentences = current_sentences + [sentence]

            candidate_text = " ".join(candidate_sentences)

            if len(candidate_text) <= self.chunk_size:
                current_sentences.append(sentence)

            else:

                if current_sentences:

                    chunk_text = " ".join(current_sentences)

                    chunks.append(
                        {
                            "text": chunk_text,
                            "metadata": {
                                "document_id": document_id,
                                "filename": filename,
                                "page_number": page_number,
                                "chunk_index": chunk_index
                            }
                        }
                    )

                    chunk_index += 1

                if self.chunk_overlap > 0:
                    current_sentences = current_sentences[
                        -self.chunk_overlap:
                    ]
                else:
                    current_sentences = []

                current_sentences.append(sentence)

        if current_sentences:

            chunk_text = " ".join(current_sentences)

            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": {
                        "document_id": document_id,
                        "filename": filename,
                        "page_number": page_number,
                        "chunk_index": chunk_index
                    }
                }
            )

        return chunks