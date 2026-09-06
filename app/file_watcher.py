from pathlib import Path
from threading import Timer, Lock
from itertools import count
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from document_ingestor import DocumentIngestor


class ReliableDocumentProcessor:

    DEBOUNCE_SECONDS = 1.5
    CHECK_INTERVAL = 0.5
    REQUIRED_STABLE_CHECKS = 2
    MAX_WAIT_SECONDS = 15

    def __init__(self, ingestor):
        self.ingestor = ingestor

        # file_path -> (timer, token)
        self.pending = {}

        # Unique token for every new filesystem event.
        self.token_counter = count(1)

        self.lock = Lock()

    def normalize(self, file_path):
        return str(
            Path(file_path).resolve()
        )

    def schedule(self, file_path):
        file_path = self.normalize(
            file_path
        )

        with self.lock:
            old_entry = self.pending.get(
                file_path
            )

            if old_entry is not None:
                old_timer, _ = old_entry
                old_timer.cancel()

            token = next(
                self.token_counter
            )

            timer = Timer(
                self.DEBOUNCE_SECONDS,
                self.wait_and_process,
                args=(
                    file_path,
                    token
                )
            )

            timer.daemon = True

            self.pending[file_path] = (
                timer,
                token
            )

            timer.start()

    def is_latest(
        self,
        file_path,
        token
    ):
        with self.lock:
            entry = self.pending.get(
                file_path
            )

            if entry is None:
                return False

            _, latest_token = entry

            return latest_token == token

    def clear_if_latest(
        self,
        file_path,
        token
    ):
        with self.lock:
            entry = self.pending.get(
                file_path
            )

            if entry is None:
                return

            _, latest_token = entry

            if latest_token == token:
                self.pending.pop(
                    file_path,
                    None
                )

    def wait_until_ready(
        self,
        file_path,
        token
    ):
        path = Path(file_path)

        start_time = time.time()
        previous_size = None
        stable_checks = 0

        while (
            time.time() - start_time
            < self.MAX_WAIT_SECONDS
        ):
            if not self.is_latest(
                file_path,
                token
            ):
                return False

            if not path.exists():
                return False

            if not path.is_file():
                return False

            try:
                current_size = (
                    path.stat().st_size
                )

            except OSError:
                time.sleep(
                    self.CHECK_INTERVAL
                )
                continue

            if current_size <= 0:
                stable_checks = 0

            elif (
                current_size
                == previous_size
            ):
                stable_checks += 1

            else:
                stable_checks = 0

            if (
                stable_checks
                >= self.REQUIRED_STABLE_CHECKS
            ):
                return True

            previous_size = current_size

            time.sleep(
                self.CHECK_INTERVAL
            )

        return False

    def wait_and_process(
        self,
        file_path,
        token
    ):
        try:
            ready = self.wait_until_ready(
                file_path,
                token
            )

            if not ready:
                return

            if not self.is_latest(
                file_path,
                token
            ):
                return

            path = Path(file_path)

            if not path.exists():
                return

            print(
                f"\nProcessing stable file: "
                f"{file_path}"
            )

            try:
                result = (
                    self.ingestor.ingest_file(
                        file_path
                    )
                )

                print(
                    f"Status: "
                    f"{result['status']}"
                )

                print(
                    f"Chunks Added: "
                    f"{result['chunks']}"
                )

            except PermissionError:
                print(
                    "File is outside "
                    "approved folders."
                )

            except FileNotFoundError:
                print(
                    "File disappeared before "
                    "indexing."
                )

            except Exception as error:
                print(
                    f"Error indexing file: "
                    f"{error}"
                )

        finally:
            self.clear_if_latest(
                file_path,
                token
            )

    def cancel(self, file_path):
        file_path = self.normalize(
            file_path
        )

        with self.lock:
            entry = self.pending.pop(
                file_path,
                None
            )

            if entry is not None:
                timer, _ = entry
                timer.cancel()

    def cancel_all(self):
        with self.lock:
            entries = list(
                self.pending.values()
            )

            self.pending.clear()

        for timer, _ in entries:
            timer.cancel()


class DocumentEventHandler(
    FileSystemEventHandler
):

    def __init__(self, ingestor):
        self.ingestor = ingestor

        self.processor = (
            ReliableDocumentProcessor(
                ingestor
            )
        )

    def is_supported(self, file_path):
        extension = (
            Path(file_path)
            .suffix
            .lower()
        )

        return (
            extension
            in self.ingestor
            .SUPPORTED_EXTENSIONS
        )

    def schedule_file(
        self,
        file_path,
        event_name
    ):
        if not self.is_supported(
            file_path
        ):
            return

        print(
            f"\n{event_name}: "
            f"{file_path}"
        )

        self.processor.schedule(
            file_path
        )

    def on_created(self, event):
        if event.is_directory:
            return

        self.schedule_file(
            event.src_path,
            "New file detected"
        )

    def on_modified(self, event):
        if event.is_directory:
            return

        self.schedule_file(
            event.src_path,
            "Modified file detected"
        )

    def on_deleted(self, event):
        if event.is_directory:
            return

        if not self.is_supported(
            event.src_path
        ):
            return

        print(
            f"\nDeleted file detected: "
            f"{event.src_path}"
        )

        self.processor.cancel(
            event.src_path
        )

        document_id = (
            self.ingestor
            .processor
            .generate_document_id(
                event.src_path
            )
        )

        self.ingestor.store.delete_document(
            document_id
        )

        print(
            "Document removed from "
            "vector database."
        )

    def on_moved(self, event):
        if event.is_directory:
            return

        old_path = Path(
            event.src_path
        )

        new_path = Path(
            event.dest_path
        )

        old_supported = (
            self.is_supported(
                old_path
            )
        )

        new_supported = (
            self.is_supported(
                new_path
            )
        )

        if (
            not old_supported
            and not new_supported
        ):
            return

        print(
            "\nFile moved or renamed:"
        )

        print(
            f"From: {old_path}"
        )

        print(
            f"To:   {new_path}"
        )

        if old_supported:
            self.processor.cancel(
                old_path
            )

            old_document_id = (
                self.ingestor
                .processor
                .generate_document_id(
                    old_path
                )
            )

            self.ingestor.store.delete_document(
                old_document_id
            )

            print(
                "Old document removed "
                "from vector database."
            )

        if new_supported:
            self.processor.schedule(
                new_path
            )


def start_watcher():
    ingestor = DocumentIngestor()

    if not ingestor.approved_folders:
        print(
            "No valid approved "
            "folders found."
        )
        return

    print(
        "\nSynchronizing existing "
        "documents..."
    )

    sync_results = (
        ingestor.ingest_all()
    )

    if not sync_results:
        print(
            "No supported "
            "documents found."
        )

    else:
        for result in sync_results:
            print(
                f"{result['filename']}: "
                f"{result['status']}"
            )

            if (
                result["status"]
                == "error"
            ):
                print(
                    f"Error: "
                    f"{result['error']}"
                )

    print(
        f"Total document chunks: "
        f"{ingestor.store.count()}"
    )

    event_handler = (
        DocumentEventHandler(
            ingestor
        )
    )

    observer = Observer()

    for folder in (
        ingestor.approved_folders
    ):
        observer.schedule(
            event_handler,
            path=str(folder),
            recursive=True
        )

        print(
            f"Watching folder: "
            f"{folder}"
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
        print(
            "\nStopping file watcher..."
        )

        # Prevent pending timers from starting
        # new indexing work during shutdown.
        event_handler.processor.cancel_all()

        observer.stop()

    observer.join()

    print(
        "File watcher stopped."
    )


if __name__ == "__main__":
    start_watcher()