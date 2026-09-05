import json
from pathlib import Path


class FolderConfig:

    def __init__(self, config_path="config/folders.json"):
        self.config_path = Path(config_path)

    def load_approved_folders(self):
        if not self.config_path.exists():
            return []

        with open(
            self.config_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        folders = data.get(
            "approved_folders",
            []
        )

        approved_folders = []

        for folder in folders:
            folder_path = Path(folder).expanduser()

            if folder_path.exists() and folder_path.is_dir():
                approved_folders.append(
                    folder_path.resolve()
                )

        return approved_folders