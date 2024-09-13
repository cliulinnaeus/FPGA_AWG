import json
import os

def load_files_to_dict(directory_path):
    """
    Helper function to load json files from a directory into a dictionary.
    Ensures that two json files with the same "name" subfield will be overwritten in the dict.
    """
    file_dict = {}
    if os.path.exists(directory_path):
        for filename in os.listdir(directory_path):
            if filename.endswith('.json'):  # Check if the file is a .json file
                file_path = os.path.join(directory_path, filename).replace('\\', '/')  # Ensure the path uses forward slashes
                if os.path.isfile(file_path):
                    with open(file_path, 'rb') as file:
                        data = json.load(file)
                        name = data["name"]
                        file_dict[name] = file_path
    return file_dict


dir_path = "./program_cfg/test_program.json"

d = load_files_to_dict(dir_path)
print(d)