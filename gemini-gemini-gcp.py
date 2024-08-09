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
with open('files/sqlout-attribute.json', 'r', encoding='utf-8') as f:
    attributes_data = json.load(f)
with open('files/sqlout-occasion.json', 'r', encoding='utf-8') as f:
    occasions_data = json.load(f)
with open('files/sqlout-relationship.json', 'r', encoding='utf-8') as f:
    relations_data = json.load(f)

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
    ids = []
    for name in names:
        for item in data:
            if item[key_name] == name:
                ids.append(item["id"])
    return ids

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

# Input for querying the model
query = "It's my father's retirement party next month. I'm looking for a thoughtful gift. He enjoys photography, cooking, and reading historical novels. However, he doesn't like sports memorabilia or electronics. What's a good gift within a $100-$150 budget?"

# Use ThreadPoolExecutor to process the attribute splits concurrently
final_response_data = None
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(process_attributes_part, attributes_part) for attributes_part in attributes_split]
    for future in as_completed(futures):
        result = future.result()
        if result:
            final_response_data = result
            break  # Stop if a valid response is found

if final_response_data:
    # Extract IDs for attributes, occasions, and relations
    attribute_ids = get_ids(final_response_data.get("attributes", []), attributes_data, "name")
    occasion_ids = get_ids(final_response_data.get("occasion", []), occasions_data, "name")
    relation_ids = get_ids(final_response_data.get("relation", []), relations_data, "name")

    # Get the price range
    price_range = final_response_data.get("price_range", [])
    min_price = price_range[0] * 100 if len(price_range) > 0 and isinstance(price_range[0], int) else ""
    max_price = price_range[1] * 100 if len(price_range) > 1 and isinstance(price_range[1], int) else ""

    # Construct the API request URL with multiple occasionId and relationshipId parameters
    api_url = (
        f'https://api.toandfrom.com/v3/recommendation/testing?isApplyFilter=true'
        f'&minPrice={min_price}'
        f'&maxPrice={max_price}'
        f'&attributeIds={",".join(attribute_ids)}'
    )

    # Append multiple occasionId and relationshipId parameters
    for occasion_id in occasion_ids:
        api_url += f'&occasionId={occasion_id}'
    for relation_id in relation_ids:
        api_url += f'&relationshipId={relation_id}'

    # Call the API and get the list of products
    headers = {
        'content-type': 'application/json',
        'revision': '2024-05-23'
    }
    response = requests.get(api_url, headers=headers, timeout=10)

    if response.status_code == 200:
        products = response.json()
        # Print the list of products
        product_list = json.dumps(products, indent=4)
    else:
        print(f"API request failed with status code {response.status_code}")
        print(f"API Response text: {response.text}")

# LOGIC TO FILTER PRODUCTS
if product_list:
    model = GenerativeModel(
        model_name=const.VERTEX_AI_MODEL,
        system_instruction=const.FILTER_PRODUCT_SYSTEM_INSTRUCTIONS
    )

    product_template = '''
        Products list:
        {0}
        
        Query: {1}
    '''
    prompt = product_template.format(product_list, query)
    response = model.generate_content([prompt])

    if not response.text:
        print("Error: Empty response from the model.")
    else:
        response_text = json.loads(response.text.replace('“', '"').replace('”', '"').replace('```', '').replace('json', '').strip())
        print(json.dumps(response_text, indent=4))

else:
    print("No products found.")
