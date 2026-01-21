# In-memory databases for the mock application

# Key: agent_id, Value: AgentResponse
agents_db = {}

# Key: thread_id, Value: ThreadResponse
threads_db = {}

# Key: thread_id, Value: List[MessageResponse]
messages_db = {}

# Key: run_id, Value: RunResponse
runs_db = {}
