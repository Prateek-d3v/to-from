import os
import vertexai
from vertexai.generative_models import GenerativeModel
import constants as const
import helper as helper
import json
import requests

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

# Function to extract IDs based on names
def get_ids(names, data, key_name):
    ids = []
    for name in names:
        for item in data:
            if item[key_name] == name:
                ids.append(item["id"])
    return ids

# Input for querying the model
query = "Can you please provide some options for a Father's Day gift? My husband spends a lot of time on a recliner. A high quality wearable blanket that doesn’t slip off. Not too long so he doesn’t trip over. Materials that’s all season. Budget: $100."
prompt = prompt_template.format(attributes, occasions, relations, query)
response = model.generate_content([prompt])

# Check if the response is empty or not
if not response.text:
    print("Error: Empty response from the model.")
else:
    response_text = response.text.replace('“', '"').replace('”', '"').replace('```', '').replace('json', '').strip()

    try:
        # Parse the JSON response
        response_data = json.loads(response_text)

        # Ensure price_range is properly formatted
        if 'price_range' in response_data:
            price_range = response_data['price_range']
            if not price_range:  # Check if the price_range is an empty list
                response_data['price_range'] = []  # Keep it as an empty list
            elif isinstance(price_range[0], str):
                price_str = price_range[0]
                if '-' in price_str:
                    price_range = [float(price.replace('$', '')) for price in price_str.split('-')]
                else:
                    price_range = [float(price_str.replace('$', '')), float(price_str.replace('$', ''))]
                response_data['price_range'] = price_range

    except json.JSONDecodeError as e:
        print("Error decoding JSON:", str(e))
        print("Response text:", response_text)
        response_data = {}

    # Extract IDs for attributes, occasions, and relations
    attribute_ids = get_ids(response_data.get("attributes", []), attributes_data, "name")
    occasion_ids = get_ids(response_data.get("occasion", []), occasions_data, "name")
    relation_ids = get_ids(response_data.get("relation", []), relations_data, "name")

    # Get the price range
    price_range = response_data.get("price_range", [])
    min_price = int(price_range[0] * 100) if len(price_range) > 0 else ""
    max_price = int(price_range[1] * 100) if len(price_range) > 1 else ""

    # print("attributes", attribute_ids)
    # print("occasions", occasion_ids)
    # print("relations", relation_ids)
    # print("minprice", min_price)
    # print("maxprice", max_price)

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

    # print("API URL", api_url)

    # Call the API and get the list of products
    headers = {
        'content-type': 'application/json',
        'revision': '2024-05-23'
    }
    response = requests.get(api_url, headers=headers, timeout=10)

    if response.status_code == 200:
        products = response.json()
        # Print the list of products
        # print(json.dumps(products, indent=4))
        product_list = json.dumps(products, indent=4)
    else:
        print(f"API request failed with status code {response.status_code}")
        print(f"API Response text: {response.text}")

# LOGIC TO FILTER PRODUCTS
model = GenerativeModel(
    model_name=const.VERTEX_AI_MODEL,
    system_instruction=const.PRODUCT_SYSTEM_INSTRUCTIONS
)

product_template = '''
    Products list:
    {0}
    
    Query: {1}
'''

if product_list:
    prompt = product_template.format(product_list, query)
    print(prompt)
    response = model.generate_content([prompt])

    if not response.text:
        print("Error: Empty response from the model.")
    else:
        print(response.text)