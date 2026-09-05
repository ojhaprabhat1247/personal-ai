from pathlib import Path
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from document_ingestor import DocumentIngestor


class DocumentEventHandler(FileSystemEventHandler):

    def __init__(self, ingestor):
        self.ingestor = ingestor

    def is_supported(self, file_path):
        extension = Path(file_path).suffix.lower()

        return (
            extension
            in self.ingestor.SUPPORTED_EXTENSIONS
        )

    def on_created(self, event):
        if event.is_directory:
            return

        if not self.is_supported(event.src_path):
            return

        print(
            f"\nNew file detected: "
            f"{event.src_path}"
        )

        result = self.ingestor.ingest_file(
            event.src_path
        )

        print(
            f"Status: {result['status']}"
        )

        print(
            f"Chunks Added: {result['chunks']}"
        )

    def on_modified(self, event):
        if event.is_directory:
            return

        if not self.is_supported(event.src_path):
            return

        print(
            f"\nModified file detected: "
            f"{event.src_path}"
        )

        result = self.ingestor.ingest_file(
            event.src_path
        )

        print(
            f"Status: {result['status']}"
        )

        print(
            f"Chunks Added: {result['chunks']}"
        )

    def on_deleted(self, event):
        if event.is_directory:
            return

        if not self.is_supported(event.src_path):
            return

        print(
            f"\nDeleted file detected: "
            f"{event.src_path}"
        )

        document_id = self.ingestor.processor.generate_document_id(
            event.src_path
        )

        self.ingestor.store.delete_document(
            document_id
        )

        print("Document removed from vector database.")
def start_watcher():
    ingestor = DocumentIngestor()

    event_handler = DocumentEventHandler(
        ingestor
    )

    observer = Observer()

    observer.schedule(
        event_handler,
        path=str(ingestor.upload_folder),
        recursive=True
    )

    observer.start()

    print(
        f"Watching folder: "
        f"{ingestor.upload_folder.resolve()}"
    )

    print(
        "Press Ctrl+C to stop."
    )

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    start_watcher()