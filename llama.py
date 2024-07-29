import os
import json
import requests
import constants as const
import helper as helper

# Set the environment variable for Google Application Credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = const.SA_ACCOUNT

# Read the attributes, occasions, and relations from text files
# attributes = helper.read_text_file(const.ATTRIBUTES_PATH)
occasions = helper.read_text_file(const.OCCASIONS_PATH)
relations = helper.read_text_file(const.RELATIONS_PATH)
attributes = "Attribute Name""T_Pet Bathroom","Synonyms""Pet grooming, Pet care, Pet supplies""Description""Items designed to maintain the cleanliness and comfort of pets, including grooming tools and hygienic products."
# occasions = "birthday, other"
# relations = "brother, spouse, father"

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
query = "I'm looking for a birthday gift for my niece. She loves history books, arts and crafts supplies and backpacks, but she doesn't like pink colors or unicorn designs. What would be a great choice within a $40 budget?"
prompt = prompt_template.format(attributes, occasions, relations, query)

# Set the URL and headers for the Llama model
ENDPOINT = "us-central1-aiplatform.googleapis.com"
REGION = "us-central1"
PROJECT_ID = const.PROJECT_ID
ACCESS_TOKEN = const.ACCESS_TOKEN  # Ensure the access token is properly set in constants

url = f"https://{ENDPOINT}/v1beta1/projects/{PROJECT_ID}/locations/{REGION}/endpoints/openapi/chat/completions"
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# Set the payload for the Llama model
payload = {
    "model": "meta/llama3-405b-instruct-maas",
    "stream": True,
    "messages": [
        {
            "role": "system",
            "content": const.SYSTEM_INSTRUCTIONS
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
}

# Make the POST request to the Llama model
response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.text)
# Initialize product_list
product_list = ""

# Check if the response is empty or not
if response.status_code != 200:
    print(f"Error: Received status code {response.status_code}")
    print("Response:", response.text)
else:
    response_json = response.json()
    if not response_json.get('choices'):
        print("Error: Empty response from the model.")
    else:
        response_text = response_json.get('choices')[0].get('message').get('content')
        response_text = response_text.replace('“', '"').replace('”', '"').replace('```', '').replace('json', '').strip()

        try:
            # Parse the JSON response
            response_data = json.loads(response_text)

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
            product_list = json.dumps(products, indent=4)
            print(product_list)
        else:
            print(f"API request failed with status code {response.status_code}")
            print(f"API Response text: {response.text}")

# LOGIC TO FILTER PRODUCTS
if product_list:
    product_template = '''
    Products list:
    {0}
    
    Query: {1}
    '''
    prompt = product_template.format(product_list, query)

    payload = {
        "model": "meta/llama3-405b-instruct-maas",
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": const.PRODUCT_SYSTEM_INSTRUCTIONS
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    # Make the POST request to the Llama model
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    # Check if the response is empty or not
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print("Response:", response.text)
    else:
        response_json = response.json()
        if not response_json.get('choices'):
            print("Error: Empty response from the model.")
        else:
            print(response_json.get('choices')[0].get('message').get('content'))
