import os
import json
import requests
import constants as const
import helper as helper
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set the environment variable for Google Application Credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = const.SA_ACCOUNT

# Suppress gRPC logging messages
os.environ['GRPC_VERBOSITY'] = 'ERROR'

# Read the attributes, occasions, and relations from text files
attributes = helper.read_text_file(const.ATTRIBUTES_PATH)
occasions = helper.read_text_file(const.OCCASIONS_PATH)
relations = helper.read_text_file(const.RELATIONS_PATH)

# Split attributes into smaller parts based on the number of elements to avoid token limit issues
def split_attributes(attributes, num_splits):
    split_size = len(attributes) // num_splits
    return [attributes[i:i + split_size] for i in range(0, len(attributes), split_size)]

attributes_split = split_attributes(attributes, 21)

# Load the JSON files for attributes, occasions, and relations
try:
    with open('files/sqlout-attribute.json', 'r', encoding='utf-8') as f:
        attributes_data = json.load(f)
    with open('files/sqlout-occasion.json', 'r', encoding='utf-8') as f:
        occasions_data = json.load(f)
    with open('files/sqlout-relationship.json', 'r', encoding='utf-8') as f:
        relations_data = json.load(f)
except FileNotFoundError as e:
    print(f"FileNotFoundError: {str(e)}")
    raise
except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {str(e)}")
    raise

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

# Function to generate content from LLaMA model
def generate_llama_content(prompt, system_instruction):
    url = f"https://{const.ENDPOINT}/v1beta1/projects/{const.PROJECT_ID}/locations/{const.REGION}/endpoints/openapi/chat/completions"
    headers = {
        "Authorization": f"Bearer {const.ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta/llama3-405b-instruct-maas",
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": system_instruction
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raises an HTTPError if the status is 4xx, 5xx
        response_json = response.json()
        
        if not response_json.get('choices'):
            print("Error: Empty response from the model.")
            return None
        
        return response_json.get('choices')[0].get('message').get('content')
    
    except requests.exceptions.RequestException as e:
        print(f"Error during the request: {str(e)}")
        return None

# Input for querying the model
query = "It's my father's retirement party next month. I'm looking for a thoughtful gift. He enjoys photography, cooking, and reading historical novels. However, he doesn't like sports memorabilia or electronics. What's a good gift within a $100-$150 budget?"

# Function to process each part of the attributes split concurrently
def process_attributes_part(attributes_part):
    prompt = prompt_template.format(attributes_part, occasions, relations, query)
    response_text = generate_llama_content(prompt, const.SYSTEM_INSTRUCTIONS)
    
    if response_text:
        try:
            response_text = response_text.replace('“', '"').replace('”', '"').replace('```', '').replace('json', '').strip()
            response_data = json.loads(response_text)
            return response_data
        except json.JSONDecodeError as e:
            print("Error decoding JSON:", str(e))
            print("Response text:", response_text)
            return None
    else:
        print("No response received for this attributes part.")
        return None

# Use ThreadPoolExecutor to process the attribute splits concurrently
attribute_ids = set()
final_response_data = None

with ThreadPoolExecutor(max_workers=21) as executor:
    futures = [executor.submit(process_attributes_part, attributes_part) for attributes_part in attributes_split]
    
    for future in as_completed(futures):
        result = future.result()
        if result:
            attribute_ids.update(get_ids(result.get("attributes", []), attributes_data, "name"))
            if not final_response_data:
                final_response_data = result  # Capture the first valid result

# Convert set back to list
attribute_ids = list(attribute_ids)

# Proceed with the remaining logic for occasions, relations, and price range
try:
    if final_response_data:
        # Extract IDs for occasions and relations
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
        product_list = ""

        if response.status_code == 200:
            products = response.json()
            product_list = json.dumps(products, indent=4)
        else:
            print(f"API request failed with status code {response.status_code}")
            print(f"API Response text: {response.text}")

except requests.exceptions.RequestException as e:
    print(f"Error during the API request: {str(e)}")
    product_list = ""

# Logic to filter products
product_template = '''
    Products list:
    {0}
    
    Query: {1}
'''

# Logic to split product_list into three parts
def split_list(lst, num_splits):
    split_size = len(lst) // num_splits
    return [lst[i:i + split_size] for i in range(0, len(lst), split_size)]

if product_list:
    # Convert product_list JSON string to a list of products
    products = json.loads(product_list)

    # Split the products list into 3 parts
    product_splits = split_list(products, 3)

    final_combined_response = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for i, product_part in enumerate(product_splits, 1):
            part_json = json.dumps(product_part, indent=4)
            part_prompt = product_template.format(part_json, query)
            
            futures.append(executor.submit(generate_llama_content, part_prompt, const.FILTER_PRODUCT_SYSTEM_INSTRUCTIONS))
        
        for i, future in enumerate(as_completed(futures), 1):
            part_response = future.result()
            if part_response:
                try:
                    part_response = part_response.replace('“', '"').replace('”', '"').replace('```', '').replace('json', '').strip()
                    part_response_data = json.loads(part_response)
                    final_combined_response.extend(part_response_data)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON for part {i}: {str(e)}")
                    print("Response text:", part_response)
            else:
                print(f"Error: Empty response from the model for part {i}.")
    
    # Print the final combined response
    print(json.dumps(final_combined_response, indent=4))
