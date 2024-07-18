import json

# Function to extract attributes from input JSON file
def extract_attributes(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    extracted_data = []
    for item in data:
        attribute_name = item.get("Attribute Name", "")
        synonyms = item.get("Synonyms", "")
        long_description = item.get("Long Description", "")
        extracted_data.append({
            "Attribute Name": attribute_name,
            "Synonyms": synonyms,
            "Long Description": long_description
        })
    
    # Write extracted data to output JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, indent=4)

# Example usage:
input_json_file = r'C:\Users\NAGA PRASSAD\Desktop\to-from\Kloudstax\Cleaned_GPT_Attributes.json'  # Replace with your input JSON file path
output_json_file = 'attr-syn-ldesc.json'  # Replace with desired output JSON file path

extract_attributes(input_json_file, output_json_file)

print(f"Extraction complete. Extracted data saved to '{output_json_file}'.")