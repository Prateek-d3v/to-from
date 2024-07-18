import json

def minify_json(input_file_path, output_file_path):
    """
    Removes spaces and indentations from a JSON file and creates a new compact JSON file.

    Parameters:
    input_file_path (str): The path to the input JSON file.
    output_file_path (str): The path to the output JSON/TXT file.
    """
    try:
        with open(input_file_path, 'r') as input_file:
            data = json.load(input_file)
        
        with open(output_file_path, 'w') as output_file:
            json.dump(data, output_file, separators=(',', ':'))
        
        print(f"Compact JSON/TXT file created at {output_file_path}")
    
    except Exception as e:
        print(f"An error occurred: {e}")


def read_text_file(file_path):
    try:
        with open(file_path, 'r', encoding="utf-8") as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None
    except IOError:
        print(f"Error: Could not read the file '{file_path}'.")
        return None
    

if __name__ == '__main__':
    input_path = r'files\Attributes.json'
    output_path = 'output.txt'
    minify_json(input_path, output_path)