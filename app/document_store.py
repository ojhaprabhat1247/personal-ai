import chromadb

import embeddings


class DocumentStore:

    def __init__(self, db_path="data/chroma"):

        self.client = chromadb.PersistentClient(
            path=db_path
        )

        self.collection = self.client.get_or_create_collection(
            name="documents"
        )

    def get_document_chunks(self, document_id):

        return self.collection.get(
            where={
                "document_id": document_id
            }
        )

    def delete_document(self, document_id):

        self.collection.delete(
            where={
                "document_id": document_id
            }
        )


    def get_all_documents(self):
        results = self.collection.get(
            include=["metadatas"]
        )

        documents = {}

        for metadata in results["metadatas"]:

            if not metadata:
                continue

            document_id = metadata.get("document_id")
            source_path = metadata.get("source_path")

            if document_id and source_path:
                documents[document_id] = source_path

        return documents
    
    def add_document(self, document):

        document_id = document["document_id"]
        file_hash = document["file_hash"]
        chunks = document["chunks"]

        existing = self.get_document_chunks(
            document_id
        )

        # File already exists in database.
        if existing["ids"]:

            existing_metadata = (
                existing["metadatas"][0]
            )

            old_hash = existing_metadata.get(
                "file_hash"
            )

            # Same file + same content.
            if old_hash == file_hash:

                return {
                    "status": "unchanged",
                    "chunks": 0
                }

            # Same file but content changed.
            self.delete_document(
                document_id
            )

        if not chunks:

            return {
                "status": "empty",
                "chunks": 0
            }

        ids = []
        documents = []
        vectors = []
        metadatas = []

        for chunk in chunks:

            text = chunk["text"]

            metadata = (
                chunk["metadata"].copy()
            )

            metadata = {
                key: value
                for key, value in metadata.items()
                if value is not None
            }

            vector = (
                embeddings.generate_embedding(
                    text
                )
            )

            chunk_index = metadata[
                "chunk_index"
            ]

            # Deterministic chunk ID.
            chunk_id = (
                f"{document_id}_{chunk_index}"
            )

            ids.append(chunk_id)
            documents.append(text)
            vectors.append(vector)
            metadatas.append(metadata)

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=vectors,
            metadatas=metadatas
        )

        return {
            "status": "indexed",
            "chunks": len(chunks)
        }

    def search(
        self,
        query,
        n_results=5
    ):

        count = self.collection.count()

        if count == 0:
            return []

        query_vector = (
            embeddings.generate_embedding(
                query
            )
        )

        results = self.collection.query(
            query_embeddings=[
                query_vector
            ],
            n_results=min(
                n_results,
                count
            ),
            include=[
                "documents",
                "metadatas",
                "distances"
            ]
        )

        matches = []

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for text, metadata, distance in zip(
            documents,
            metadatas,
            distances
        ):

            matches.append(
                {
                    "text": text,
                    "metadata": metadata,
                    "distance": distance
                }
            )

        return matches

    def count(self):

        return self.collection.count()