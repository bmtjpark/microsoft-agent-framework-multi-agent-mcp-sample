import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv(dotenv_path="src/.env")

conn_str = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
client = AIProjectClient(
    endpoint=conn_str,
    credential=DefaultAzureCredential()
)

with client:
    # openai_client = client.inference.get_chat_completions_client()
    # It seems SDK usage might be slightly different. 
    # Let's try to list deployments or models if possible via standard OpenAI API?
    # Actually client.get_openai_client() returns an AzureOpenAI (or OpenAI) client.
    
    # aoai_client = client.get_openai_client()
    # print(f"Base URL: {aoai_client.base_url}")
    # try:
    #     # Standard OpenAI list models
    #     models = aoai_client.models.list()
    #     for m in models:
    #         print(f"Model: {m.id}")
    # except Exception as e:
    #     print(f"Error listing models: {e}")

    print("Attempting inference with 'gpt-4o-mini'...")
    try:
        inference_client = client.inference.get_chat_completions_client()
        response = inference_client.complete(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}]
        )
        print("Success!")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Inference failed: {e}")
