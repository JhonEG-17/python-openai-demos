import csv
import os

import azure.identity
import openai
from dotenv import load_dotenv
from lunr import lunr

# Setup the OpenAI client to use either Azure, OpenAI.com, or Ollama API
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST")

if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    client = openai.AzureOpenAI(
        api_version=os.environ["AZURE_OPENAI_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_ad_token_provider=token_provider,
    )
    MODEL_NAME = os.environ["AZURE_OPENAI_DEPLOYMENT"]

elif API_HOST == "ollama":
    client = openai.OpenAI(base_url=os.environ["OLLAMA_ENDPOINT"], api_key="nokeyneeded")
    MODEL_NAME = os.environ["OLLAMA_MODEL"]

elif API_HOST == "github":
    client = openai.OpenAI(base_url="https://models.inference.ai.azure.com", api_key=os.environ["GITHUB_TOKEN"])
    MODEL_NAME = os.environ["GITHUB_MODEL"]

else:
    client = openai.OpenAI(api_key=os.environ["OPENAI_KEY"])
    MODEL_NAME = os.environ["OPENAI_MODEL"]

# Index the data from the CSV
with open("hybrid.csv") as file:
    reader = csv.reader(file)
    rows = list(reader)
documents = [{"id": (i + 1), "body": " ".join(row)} for i, row in enumerate(rows[1:])]
index = lunr(ref="id", fields=["body"], documents=documents)


def search(query):
    # Search the index for the user question
    query = query.lower().replace("?", "")
    results = index.search(query)
    matching_rows = [rows[int(result["ref"])] for result in results]

    # Format as a markdown table, since language models understand markdown
    matches_table = " | ".join(rows[0]) + "\n" + " | ".join(" --- " for _ in range(len(rows[0]))) + "\n"
    matches_table += "\n".join(" | ".join(row) for row in matching_rows)
    return matches_table


SYSTEM_MESSAGE = """
You are a helpful assistant that answers questions about cars based off a hybrid car data set.
You must use the data set to answer the questions, you should not provide any info that is not in the provided sources.
"""
messages = [{"role": "system", "content": SYSTEM_MESSAGE}]

while True:
    question = input("\nYour question about electric cars: ")

    # Search the CSV for the question
    matches = search(question)
    print("Found matches:\n")
    print(matches)

    # Use the matches to generate a response
    messages.append({"role": "user", "content": f"{question}\nSources: {matches}"})
    response = client.chat.completions.create(model=MODEL_NAME, temperature=0.3, messages=messages)

    bot_response = response.choices[0].message.content
    messages.append({"role": "assistant", "content": bot_response})

    print(f"\nResponse from {API_HOST} {MODEL_NAME}: \n")
    print(bot_response)
