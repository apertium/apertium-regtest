import os
import json

def merge_tests_json(output_path, file1_path, file2_path):
    """
    Merges two JSON files into one.
    
    :param file1_path: Path to the first JSON file.
    :param file2_path: Path to the second JSON file.
    :param output_path: Path to save the merged JSON file.
    """
    try:
        with open(file1_path, 'r') as f1:
            data1 = json.load(f1)

        with open(file2_path, 'r') as f2:
            data2 = json.load(f2)

        merged_data = {**data1, **data2}

        with open(output_path, 'w') as f_out:
            json.dump(merged_data, f_out, indent=4)

        print("Files have been merged successfully.")
    except Exception as e:
        print(f"Error merging files: {e}")

