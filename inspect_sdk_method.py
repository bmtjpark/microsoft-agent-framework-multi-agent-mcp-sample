from azure.ai.projects import AIProjectClient
import inspect
print(inspect.signature(AIProjectClient.get_openai_client))