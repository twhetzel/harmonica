from openai import OpenAI
client = OpenAI()
import json


condition = "ASD"

completion = client.chat.completions.create(
#   model="gpt-3.5-turbo",
  model="gpt-3.5-turbo-0125",
  response_format={ "type": "json_object" },
  messages=[
    {"role": "system", "content": "You are a helpful biomedical data curator with a background in human diseases and human genetics designed to output JSON."},
    {"role": "user", "content": f"What are other medical conditions are represented by the abbreviation {condition}? \
     Return this as a list. \
     The key of the content message should be conditions."}
  ]
)

# print(completion.choices[0].message)
# print(json.dumps(json.loads(completion.model_dump_json()), indent=4))

print(json.dumps(json.loads(completion.choices[0].message.model_dump_json()), indent=4))

response_content = json.dumps(json.loads(completion.choices[0].message.model_dump_json()))
print(response_content)

# Parse JSON data into a Python dictionary
data = json.loads(response_content)

# Access the 'conditions' list from the dictionary
conditions = data['content']

# Parse the 'conditions' list from the string
conditions_data = json.loads(conditions)

# Access and print each condition
for condition in conditions_data['conditions']:
    print(condition)