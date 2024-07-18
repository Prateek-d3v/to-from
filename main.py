import os
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

# Input loop for querying the model
query = input("Query: ")
while query != 'q':
    prompt = prompt_template.format(attributes, occasions, relations, query)
    response = model.generate_content([prompt])
    print(response.text)
    
    # Ask for a new query
    query = input("User Query: ")

print('Bye!')