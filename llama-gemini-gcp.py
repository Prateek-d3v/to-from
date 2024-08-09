import os
import json
import requests
import constants as const
import helper as helper
from vertexai.generative_models import GenerativeModel
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set environment variables
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = const.SA_ACCOUNT
os.environ['GRPC_VERBOSITY'] = 'ERROR'

# Read data from files
attributes = helper.read_text_file(const.ATTRIBUTES_PATH)
occasions = helper.read_text_file(const.OCCASIONS_PATH)
relations = helper.read_text_file(const.RELATIONS_PATH)

# Function to split attributes for processing in smaller parts
def split_attributes(attributes, num_splits):
    split_size = len(attributes) // num_splits
    return [attributes[i:i + split_size] for i in range(0, len(attributes), split_size)]

attributes_split = split_attributes(attributes, 21)

# Load the JSON data for attributes, occasions, and relations
def load_json_data(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

attributes_data = load_json_data('files/sqlout-attribute.json')
occasions_data = load_json_data('files/sqlout-occasion.json')
relations_data = load_json_data('files/sqlout-relationship.json')

# Prompt template
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
    return [item["id"] for name in names for item in data if item[key_name] == name]

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
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        response_json = response.json()
        if response_json.get('choices'):
            return response_json['choices'][0]['message']['content']
    return None

# Process attributes in parts using threading
final_response_data = None

def process_attributes_part(attributes_part):
    global final_response_data
    prompt = prompt_template.format(attributes_part, occasions, relations, query)
    response_text = generate_llama_content(prompt, const.SYSTEM_INSTRUCTIONS)
    
    if response_text:
        response_text = response_text.replace('“', '"').replace('”', '"').replace('```', '').replace('json', '').strip()

        try:
            response_data = json.loads(response_text)
            final_response_data = response_data  # Capture the response data
            return get_ids(response_data.get("attributes", []), attributes_data, "name")
        except json.JSONDecodeError as e:
            print("Error decoding JSON:", str(e))
    return []

# Main function to execute the workflow
def main(query):
    global final_response_data
    attribute_ids = set()

    # Process the attribute splits concurrently
    with ThreadPoolExecutor(max_workers=21) as executor:
        futures = [executor.submit(process_attributes_part, attributes_part) for attributes_part in attributes_split]
        for future in as_completed(futures):
            attribute_ids.update(future.result())

    # Convert set back to list
    attribute_ids = list(attribute_ids)

    if final_response_data:
        # Extract occasion and relation IDs
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

        # Filter products using LLaMA model
        if product_list:
            model = GenerativeModel(
                model_name=const.VERTEX_AI_MODEL,
                system_instruction=const.RANK_PRODUCT_SYSTEM_INSTRUCTIONS
            )
            product_template = f"Products list:\n{product_list}\n\nQuery: {query}"
            response = model.generate_content([product_template])

            if response.text:
                response_text = json.loads(response.text.replace('“', '"').replace('”', '"').replace('```', '').replace('json', '').strip())
                return {
                    "attributes": final_response_data.get("attributes"),
                    "debug": json.loads(product_list),
                    "products": response_text
                }
            else:
                print({"error": "Empty response from the model."})
    return None

# Query input
query = "It's my father's retirement party next month. I'm looking for a thoughtful gift. He enjoys photography, cooking, and reading historical novels. However, he doesn't like sports memorabilia or electronics. What's a good gift within a $100-$150 budget?"

# Execute the main function
result = main(query)
if result:
    # Print the result in JSON format
    print(json.dumps(result, indent=4))
else:
    print(json.dumps({"error": "No result returned."}, indent=4))
