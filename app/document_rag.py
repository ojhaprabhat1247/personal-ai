from document_store import DocumentStore
import llm


class DocumentRAG:

    def __init__(self, n_results=5):
        self.store = DocumentStore()
        self.n_results = n_results

    def retrieve(self, query):
        results = self.store.search(
            query=query,
            n_results=self.n_results
        )

        if not results:
            return []

        best_distance = results[0]["distance"]

        filtered_results = []

        for result in results:
            distance = result["distance"]

            if distance <= best_distance * 1.25:
                filtered_results.append(result)

        return filtered_results

    def build_context(self, results):
        context_parts = []

        for index, result in enumerate(
            results,
            start=1
        ):
            text = result["text"]
            metadata = result["metadata"]

            filename = metadata.get(
                "filename",
                "Unknown"
            )

            page_number = metadata.get(
                "page_number"
            )

            sheet_name = metadata.get(
                "sheet_name"
            )

            source_lines = [
                f"SOURCE_ID: SOURCE_{index}",
                f"SOURCE: {filename}"
            ]

            if page_number is not None:
                source_lines.append(
                    f"PAGE: {page_number}"
                )

            if sheet_name:
                source_lines.append(
                    f"SHEET: {sheet_name}"
                )

            source_lines.append(
                f"CONTENT:\n{text}"
            )

            context_parts.append(
                "\n".join(source_lines)
            )

        return "\n\n---\n\n".join(
            context_parts
        )

    def ask(self, query):
        results = self.retrieve(query)

        if not results:
            return {
                "answer": (
                    "No relevant document "
                    "information found."
                ),
                "sources": []
            }

        context = self.build_context(
            results
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a document "
                    "question-answering assistant. "
                    "Answer using only the supplied "
                    "document context. "
                    "Do not invent information. "
                    "If the answer is not supported "
                    "by the context, say that the "
                    "information was not found. "
                    "After your answer, write "
                    "USED_SOURCES: followed only by "
                    "the SOURCE_ID values that "
                    "directly support your answer. "
                    "Do not cite a source unless it "
                    "directly supports the answer."
                )
            },
            {
                "role": "user",
                "content": (
                    f"DOCUMENT CONTEXT:\n\n"
                    f"{context}\n\n"
                    f"QUESTION:\n{query}\n\n"
                    "Required format:\n"
                    "ANSWER: <your answer>\n"
                    "USED_SOURCES: "
                    "SOURCE_1, SOURCE_2"
                )
            }
        ]

        response = llm.generate(
            messages=messages,
            stream=False
        )

        if isinstance(response, dict):
            raw_answer = (
                response["message"]["content"]
            )
        else:
            raw_answer = (
                response.message.content
            )

        answer = raw_answer
        used_source_ids = []

        if "USED_SOURCES:" in raw_answer:
            answer_part, source_part = (
                raw_answer.split(
                    "USED_SOURCES:",
                    1
                )
            )

            answer = answer_part.strip()

            if answer.startswith("ANSWER:"):
                answer = answer[
                    len("ANSWER:"):
                ].strip()

            source_text = (
                source_part.strip()
            )

            for item in source_text.split(","):
                source_id = item.strip()

                if source_id.startswith(
                    "SOURCE_"
                ):
                    used_source_ids.append(
                        source_id
                    )

        sources = []
        seen = set()

        for source_id in used_source_ids:
            try:
                source_index = int(
                    source_id.replace(
                        "SOURCE_",
                        ""
                    )
                ) - 1

            except ValueError:
                continue

            if (
                source_index < 0
                or source_index >= len(results)
            ):
                continue

            metadata = (
                results[source_index][
                    "metadata"
                ]
            )

            source = {
                "filename": metadata.get(
                    "filename"
                ),
                "page_number": metadata.get(
                    "page_number"
                ),
                "sheet_name": metadata.get(
                    "sheet_name"
                )
            }

            key = (
                source["filename"],
                source["page_number"],
                source["sheet_name"]
            )

            if key not in seen:
                sources.append(source)
                seen.add(key)

        return {
            "answer": answer,
            "sources": sources
        }