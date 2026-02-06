import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

_client = None
_inference_client = None

def get_project_client() -> AIProjectClient:
    global _client
    if _client is None:
        conn_str = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
        if not conn_str:
            raise ValueError("AZURE_AI_PROJECT_CONNECTION_STRING environment variable is not set")
        
        # Manually parse connection string if needed because 'from_connection_string' is missing in v2.0.0b3
        if ";" in conn_str:
             parts = conn_str.split(";")
             # Expecting: <host_name>;<subscription_id>;<resource_group_name>;<project_name>
             if len(parts) >= 4:
                 host, sub, rg, project = parts[0], parts[1], parts[2], parts[3]
                 _client = AIProjectClient(
                     endpoint=f"https://{host}",
                     credential=DefaultAzureCredential(),
                     subscription_id=sub,
                     resource_group=rg,
                     project_name=project
                 )
             else:
                 # Fallback: hope it works as endpoint?
                 _client = AIProjectClient(
                    endpoint=conn_str,
                    credential=DefaultAzureCredential(),
                 )
        else:
            _client = AIProjectClient(
                endpoint=conn_str,
                credential=DefaultAzureCredential(),
            )
            
    return _client

def get_agents_client():
    project_client = get_project_client()
    return project_client.agents

def get_inference_client():
    global _inference_client
    if _inference_client is None:
        project_client = get_project_client()
        # Use the project client's inference client (Gateway)
        # 2.0.0b3 typically defaults to a valid version.
        _inference_client = project_client.get_openai_client(
             # Use the version that worked for simple chat to ensure connectivity
             # default_query={"api-version": "2024-10-01-preview"}
        )
        
        # FIX: The Azure AI Project Gateway (using get_openai_client) constructs a base URL like:
        # https://<region>.api.azureml.ms/projects/<id>/openai
        # However, for Assistants API (Beta), the "/openai" suffix is often NOT required or causes 404
        # when combined with "/threads" endpoint.
        #
        # Correct pattern for Gateway Assistants: https://<region>.api.azureml.ms/projects/<id>/threads
        # Current SDK constructs: https://<region>.api.azureml.ms/projects/<id>/openai/threads -> 404
        
        base_url_str = str(_inference_client.base_url)
        # Fix logic removed as it was causing 404s in this environment
        if base_url_str.endswith("/openai/") or base_url_str.endswith("/openai"):
             pass
             # import re
             # Remove /openai or /openai/ from the end
             # new_base = re.sub(r"/openai/?$", "/", base_url_str.rstrip("/"))
             # _inference_client.base_url = new_base
            
    return _inference_client

