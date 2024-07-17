import json

# Load the data from the input JSON file
with open(r'C:\Users\NAGA PRASSAD\Desktop\to-from\Kloudstax\Cleaned_GPT_Attributes.json', 'r') as infile:
    data = json.load(infile)

# Extract the required data
extracted_data = {item["Attribute Name"]: item["Long Description"] for item in data}

# Write the extracted data to a new JSON file
with open('extracted_data.json', 'w') as outfile:
    json.dump(extracted_data, outfile, indent=4)

print("Data extracted and written to extracted_data.json")
