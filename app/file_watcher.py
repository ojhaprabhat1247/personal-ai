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

        try:
            result = self.ingestor.ingest_file(
                event.src_path
            )

            print(
                f"Status: {result['status']}"
            )

            print(
                f"Chunks Added: {result['chunks']}"
            )

        except Exception as error:
            print(
                f"Error indexing file: {error}"
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

        try:
            result = self.ingestor.ingest_file(
                event.src_path
            )

            print(
                f"Status: {result['status']}"
            )

            print(
                f"Chunks Added: {result['chunks']}"
            )

        except Exception as error:
            print(
                f"Error indexing file: {error}"
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

        document_id = (
            self.ingestor.processor.generate_document_id(
                event.src_path
            )
        )

        self.ingestor.store.delete_document(
            document_id
        )

        print(
            "Document removed from vector database."
        )

    def on_moved(self, event):
        if event.is_directory:
            return

        old_path = Path(event.src_path)
        new_path = Path(event.dest_path)

        old_supported = self.is_supported(old_path)
        new_supported = self.is_supported(new_path)

        if not old_supported and not new_supported:
            return

        print(
            f"\nFile moved or renamed:\n"
            f"From: {old_path}\n"
            f"To:   {new_path}"
        )

        if old_supported:
            old_document_id = (
                self.ingestor.processor.generate_document_id(
                    old_path
                )
            )

            self.ingestor.store.delete_document(
                old_document_id
            )

            print(
                "Old document removed from vector database."
            )

        if new_supported:
            try:
                result = self.ingestor.ingest_file(
                    new_path
                )

                print(
                    f"Status: {result['status']}"
                )

                print(
                    f"Chunks Added: {result['chunks']}"
                )

            except PermissionError:
                print(
                    "New location is outside approved folders."
                )

            except Exception as error:
                print(
                    f"Error indexing moved file: {error}"
                )

def start_watcher():
    ingestor = DocumentIngestor()

    if not ingestor.approved_folders:
        print(
            "No valid approved folders found."
        )
        return

    
    print("\nSynchronizing existing documents...")

    sync_results = ingestor.ingest_all()

    if not sync_results:
        print("No supported documents found.")

    else:
        for result in sync_results:
            print(
                f"{result['filename']}: "
                f"{result['status']}"
            )

            if result["status"] == "error":
                print(
                    f"Error: {result['error']}"
                )

    print(
        f"Total document chunks: "
        f"{ingestor.store.count()}"
    )
    
    event_handler = DocumentEventHandler(
        ingestor
    )

    observer = Observer()

    for folder in ingestor.approved_folders:

        observer.schedule(
            event_handler,
            path=str(folder),
            recursive=True
        )

        print(
            f"Watching folder: {folder}"
        )

    observer.start()

    print(
        "\nFile watcher started."
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