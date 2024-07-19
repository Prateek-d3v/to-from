import os
import vertexai
from vertexai.generative_models import GenerativeModel
import constants as const
import helper as helper

# Set the environment variable for Google Application Credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = const.SA_ACCOUNT

# Initialize Vertex AI
vertexai.init(project=const.PROJECT_ID, location=const.VERTEX_AI_LOCATION)

# Initialize the generative model for attributes
attributes_model = GenerativeModel(
    model_name=const.VERTEX_AI_MODEL,
    system_instruction=const.SYSTEM_INSTRUCTIONS_ATTRIBUTE,
)

# Read the attributes from text files
attributes = helper.read_text_file(const.ATTRIBUTES_PATH)

# Define the prompt template for attributes
attributes_prompt_template = """
Attributes:
{0}
Query: {1}
"""

# Initialize the generative model for the main query
model = GenerativeModel(
    model_name=const.VERTEX_AI_MODEL, system_instruction=const.SYSTEM_INSTRUCTIONS
)

# Read the occasions and relations from text files
occasions = helper.read_text_file(const.OCCASIONS_PATH)
relations = helper.read_text_file(const.RELATIONS_PATH)

# Define the prompt template for the main query
main_prompt_template = """
Attributes:
{0}
Occasions:
{1}
Relations:
{2}
Query: {3}
"""


# Input loop for querying the model
main_query = input("Query: ")
while main_query.lower() != "q":
    attributes_prompt = attributes_prompt_template.format(attributes, main_query)
    attributes_response = attributes_model.generate_content([attributes_prompt])

    # # Print the response for debugging
    # print("Attributes Response:", attributes_response.text)

    # Create the query for the main model
    query = f"{main_query} Here are some of the attributes: {', '.join(attributes_response.text)}. Add some more relevant attributes to it."

    main_prompt = main_prompt_template.format(attributes, occasions, relations, query)
    response = model.generate_content([main_prompt])
    print(response.text)

    # Ask for a new query
    main_query = input("Query: ")

print("Bye!")
