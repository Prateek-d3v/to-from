import os
import json
import requests
import vertexai
from vertexai.generative_models import GenerativeModel
import constants as const
import helper as helper

# Set the environment variable for Google Application Credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = const.SA_ACCOUNT

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
with open('files/sqlout-attribute.json', 'r') as f:
    attributes_data = json.load(f)
with open('files/sqlout-occasion.json', 'r') as f:
    occasions_data = json.load(f)
with open('files/sqlout-relationship.json', 'r') as f:
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

# Input loop for querying the model
query = input("Query: ")
while query != 'q':
    prompt = prompt_template.format(attributes, occasions, relations, query)
    response = model.generate_content([prompt])
    
    # Check if the response is empty or not
    if not response.text:
        print("Error: Empty response from the model.")
        query = input("User Query: ")
        continue
    
    response_text = response.text.replace('“', '"').replace('”', '"').replace('```', '').replace('json', '').strip()

    try:
        # Parse the JSON response
        response_data = json.loads(response_text)
    
        # Ensure price_range is properly formatted
        if 'price_range' in response_data:
            price_range = response_data['price_range']
            if isinstance(price_range[0], str):
                price_range = [float(price.replace('$', '')) for price in price_range[0].split('-')]
                response_data['price_range'] = price_range

    except json.JSONDecodeError as e:
        print("Error decoding JSON:", str(e))
        print("Response text:", response_text)
        query = input("User Query: ")
        continue
    
    # Extract IDs for attributes, occasions, and relations
    attribute_ids = get_ids(response_data["attributes"], attributes_data, "name")
    occasion_ids = get_ids(response_data["occasion"], occasions_data, "name")
    relation_ids = get_ids(response_data["relation"], relations_data, "name")
    
    # Get the price range
    price_range = response_data.get("price_range", [])
    min_price = price_range[0] if price_range else ""
    max_price = price_range[1] if len(price_range) > 1 else ""

    print("attributes", attribute_ids)
    print("occasions", occasion_ids)
    print("relations", relation_ids)
    print("minprice", min_price)
    print("maxprice", max_price)
    
    # Construct the API request URL
    api_url = (
        f'https://api.toandfrom.com/v3/recommendation/testing?isApplyFilter=true'
        f'&occasionId={",".join(occasion_ids)}'
        f'&relationshipId={",".join(relation_ids)}'
        f'&minPrice={min_price}'
        f'&maxPrice={max_price}'
        f'&attributeIds={",".join(attribute_ids)}'
    )
    
    # Call the API and get the list of products
    headers = {
        'content-type': 'application/json',
        'revision': '2024-05-23'
    }
    response = requests.post(api_url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        products = response.json()
        # Print the list of products
        print(json.dumps(products, indent=4))
    else:
        print(f"API request failed with status code {response.status_code}")
        print(f"Response text: {response.text}")
    
    # Ask for a new query
    query = input("User Query: ")

print('Bye!')
