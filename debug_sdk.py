import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
print(f"Endpoint/ConnStr: {ENDPOINT}")

try:
    client = AIProjectClient(
        endpoint=ENDPOINT, # Trying as endpoint
    print("Client created successfully.")
    print("AIProjectClient attributes:", dir(client))
    
    if hasattr(client, 'connections'):
        print("\nListing connections:")
        try:
            for conn in client.connections.list():
                print(f" - {conn.name} ({conn.type})")
        except Exception as e:
            print(f"Error listing connections: {e}")

except Exception as e:
    print(f"Error: {e}")
