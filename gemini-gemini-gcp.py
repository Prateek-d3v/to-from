import os
import vertexai
from vertexai.generative_models import GenerativeModel
import constants as const
import helper as helper
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set the environment variable for Google Application Credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = const.SA_ACCOUNT

# Suppress gRPC logging messages
os.environ['GRPC_VERBOSITY'] = 'ERROR'

# Optionally, suppress TensorFlow logging messages
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Initialize Vertex AI
vertexai.init(project=const.PROJECT_ID, location=const.VERTEX_AI_LOCATION)

# Initialize the generative model
model = GenerativeModel(
    model_name=const.VERTEX_AI_MODEL,
    system_instruction=const.SYSTEM_INSTRUCTIONS
)

# Read the attributes, occasions, and relations from text files
attributes = helper.read_text_file(const.ATTRIBUTES_PATH)
occasions = helper.read_text_file(const.OCCASIONS_PATH)
relations = helper.read_text_file(const.RELATIONS_PATH)

# Load the attributes, occasions, and relations JSON files
def load_json_data(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

attributes_data = load_json_data('files/sqlout-attribute.json')
occasions_data = load_json_data('files/sqlout-occasion.json')
relations_data = load_json_data('files/sqlout-relationship.json')

# Define the prompt template
prompt_template = """
Attributes:
{0}
Occasions:
{1}
Relations:
{2}
Query: {3}
"""

# Function to split attributes into smaller parts based on number of elements
def split_attributes(attributes, num_splits):
    split_size = len(attributes) // num_splits
    return [attributes[i:i + split_size] for i in range(0, len(attributes), split_size)]

# Split attributes into smaller parts
attributes_split = split_attributes(attributes, 21)

# Function to extract IDs based on names
def get_ids(names, data, key_name):
    return [item["id"] for name in names for item in data if item[key_name] == name]

# Function to process each part of attributes and generate a response
def process_attributes_part(attributes_part):
    prompt = prompt_template.format(attributes_part, occasions, relations, query)
    response = model.generate_content([prompt])

    if response.text:
        response_text = response.text.replace('“', '"').replace('”', '"').replace('```', '').replace('json', '').strip()
        try:
            # Parse the JSON response
            response_data = json.loads(response_text)
            return response_data
        except json.JSONDecodeError as e:
            print("Error decoding JSON:", str(e))
            print("Response text:", response_text)
            return None
    return None

# Main function to execute the workflow
def main(query):
    all_attributes = []
    final_response_data = None

    # Process the attribute splits concurrently
    with ThreadPoolExecutor(max_workers=21) as executor:
        futures = [executor.submit(process_attributes_part, attributes_part) for attributes_part in attributes_split]
        for future in as_completed(futures):
            result = future.result()
            if result:
                # Combine attributes from all threads
                all_attributes.extend(result.get("attributes", []))
                if not final_response_data:
                    final_response_data = result  # Capture the first valid result

    # Deduplicate the attributes
    all_attributes = list(set(all_attributes))

    if final_response_data:
        # Extract occasion and relation IDs
        attribute_ids = get_ids(all_attributes, attributes_data, "name")
        occasion_ids = get_ids(final_response_data.get("occasion", []), occasions_data, "name")
        relation_ids = get_ids(final_response_data.get("relation", []), relations_data, "name")

        # Get price range
        price_range = final_response_data.get("price_range", [])
        min_price = price_range[0] * 100 if len(price_range) > 0 and isinstance(price_range[0], int) else ""
        max_price = price_range[1] * 100 if len(price_range) > 1 and isinstance(price_range[1], int) else ""

        # Construct the API request URL
        api_url = (
            f'https://api.toandfrom.com/v3/recommendation/testing?isApplyFilter=true'
            f'&minPrice={min_price}&maxPrice={max_price}'
            f'&attributeIds={",".join(attribute_ids)}'
        )

        # Append occasionId and relationshipId parameters
        for occasion_id in occasion_ids:
            api_url += f'&occasionId={occasion_id}'
        for relation_id in relation_ids:
            api_url += f'&relationshipId={relation_id}'

        # Make API call to fetch product recommendations
        headers = {
            'content-type': 'application/json',
            'revision': '2024-05-23'
        }
        response = requests.get(api_url, headers=headers, timeout=10)
        product_list = ""

        if response.status_code == 200:
            products = response.json()
            product_list = json.dumps(products, indent=4)
        else:
            print(f"API request failed with status code {response.status_code}")
            print(f"API Response text: {response.text}")

        # Filter products using Vertex AI model
        if product_list:
            model = GenerativeModel(
                model_name=const.VERTEX_AI_MODEL,
                system_instruction=const.FILTER_PRODUCT_SYSTEM_INSTRUCTIONS
            )
            product_template = f"Products list:\n{product_list}\n\nQuery: {query}"
            response = model.generate_content([product_template])

            if response.text:
                response_text = json.loads(response.text.replace('“', '"').replace('”', '"').replace('```', '').replace('json', '').strip())
                return {
                    "attributes": all_attributes,
                    "debug": json.loads(product_list),
                    "products": response_text
                }
            else:
                print({"error": "Empty response from the model."})
    return None

# Query input
query = "Gifts for my 10 year old kid for his birthday. He likes video games, novels, tech gadgets, something creative, travelling and he is also a sports lover. My budget is $150."

# Execute the main function
result = main(query)
if result:
    # Print the result in JSON format
    print(json.dumps(result, indent=4))
else:
    print(json.dumps({"error": "No result returned."}, indent=4))
