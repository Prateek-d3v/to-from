import os
import vertexai
from vertexai.generative_models import GenerativeModel
import constants as const
import helper as helper

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = const.SA_ACCOUNT

vertexai.init(project=const.PROJECT_ID, location=const.VERTEX_AI_LOCATION)

model = GenerativeModel(
    model_name=const.VERTEX_AI_MODEL,
    system_instruction=[const.SYSTEM_INSTRUCTIONS],
)

attributes = helper.read_text_file(const.ATTRIBUTES_PATH)
occasions = helper.read_text_file(const.OCCASIONS_PATH)
relations = helper.read_text_file(const.RELATIONS_PATH)


prompt = """
Attributes:
{attributes}
Occasions:
{occasions}
Relations:
{relations}
Query: Look for a Father’s Day gift for my husband from his 11 year old and from me. He is 41 and enjoys cigars, camping, smoking meats like bbq.
"""

contents = [prompt]

response = model.generate_content(contents)
print(response.text)