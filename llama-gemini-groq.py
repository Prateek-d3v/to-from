import os
import requests
import constants as const
import helper as helper
from vertexai.generative_models import GenerativeModel
from groq import Groq
import json

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
query = "Gifts for my nephew who is turning 13. He’s a sports nut and loves hockey and football - especially the 49ers. He is also really into all things tech. My budget is around $100."

prompt = prompt_template.format(attributes, occasions, relations, query)

client = Groq(
    # api_key=os.environ.get("GROQ_API_KEY"),
    api_key='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'
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": const.SYSTEM_INSTRUCTIONS
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    # model="llama3-8b-8192", # Limit 30000
    model="llama-3.1-70b-versatile",
    # model="llama-3.1-405b-reasoning", # does not exist or you do not have access to it
    # model="llama3-70b-8192", # Limit 6000
    # model="mixtral-8x7b-32768", # Limit 5000
    # model="gemma2-9b-it",  # Limit 15000,
    # model="gemma-7b-it", # Limit 15000,
    # model="llama3-groq-70b-8192-tool-use-preview", # Limit 15000
    # stream=True,
    top_p=1,
    temperature=0.1
)

print(chat_completion.choices[0].message.content)


# Check if the response is empty or not
if not chat_completion.choices[0].message.content:
    print("Error: Empty response from the model.")
else:
    response_text = chat_completion.choices[0].message.content.replace('“', '"').replace('”', '"').replace('```', '').replace('json', '').strip()

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
    min_price = price_range[0] * 100 if len(price_range) > 0 and isinstance(price_range[0], int) else ""
    max_price = price_range[1] * 100 if len(price_range) > 1 and isinstance(price_range[1], int) else ""

    # Construct the API request URL with multiple occasionId and relationshipId parameters
    api_url = (
        f'https://api.toandfrom.com/v3/recommendation/testing?isApplyFilter=true'
        f'&minPrice={min_price}'
        f'&maxPrice={max_price}'
        f'&attributeIds={" ,".join(attribute_ids)}'
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
    system_instruction=const.PRODUCT_SYSTEM_INSTRUCTIONS,
    generation_config=const.GENERATION_CONFIG
)

product_template = '''
    Products list:
    {0}
    
    Query: {1}
'''

if product_list:
    prompt = product_template.format(product_list, query)
    # print(prompt)
    response = model.generate_content([prompt])

    if not response.text:
        print("Error: Empty response from the model.")
    else:
        print(response.text)

