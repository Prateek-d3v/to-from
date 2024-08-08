import json
import requests
import constants as const

# Path to your service account key file
SERVICE_ACCOUNT_FILE = const.SA_ACCOUNT

# Set the environment variables
ENDPOINT = "us-central1-aiplatform.googleapis.com"
REGION = "us-central1"
PROJECT_ID = const.PROJECT_ID


access_token = const.ACCESS_TOKEN
# Set the URL
url = f"https://{ENDPOINT}/v1beta1/projects/{PROJECT_ID}/locations/{REGION}/endpoints/openapi/chat/completions"

# Set the headers
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Set the payload
payload = {
    "model": "meta/llama3-405b-instruct-maas",
    "stream": False,
    "messages": [
        {
            "role": "user",
            "content": "Summer travel plan to Paris"
        }
    ]
}

# Make the POST request
response = requests.post(url, headers=headers, data=json.dumps(payload))

# Parse the response
response_json = json.loads(response.text)

# Extract the content
content = response_json.get('choices')[0].get('message').get('content')

print(content)
