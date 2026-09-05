from folder_config import FolderConfig


config = FolderConfig()

folders = config.load_approved_folders()

print("Approved folders:")

for folder in folders:
    print(folder)