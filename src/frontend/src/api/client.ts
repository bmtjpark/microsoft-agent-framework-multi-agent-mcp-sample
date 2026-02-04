import axios from 'axios';
import type { Agent, Message, Run, Thread, FileData, AgentCreate } from '../types';

const client = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});


export const api = {
  // Agents
  getAgents: () => client.get<Agent[]>('/agents').then(r => r.data),
  createAgent: (agent: AgentCreate) => client.post<Agent>('/agents', agent).then(r => r.data),
  deleteAgent: (agentId: string) => client.delete(`/agents/${agentId}`).then(r => r.data),
  getAgentThread: (agentId: string) => client.get<{thread_id: string | null}>(`/agents/${agentId}/thread`).then(r => r.data),
  setAgentThread: (agentId: string, threadId: string) => client.post<{thread_id: string}>(`/agents/${agentId}/thread`, { thread_id: threadId }).then(r => r.data),
  
  // Threads
  createThread: () => client.post<Thread>('/threads', {}).then(r => r.data),
  getMessages: (threadId: string) => client.get<Message[]>(`/threads/${threadId}/messages`).then(r => r.data),
  createMessage: (threadId: string, content: string, attachments: {id: string, type: string}[] = []) => 
    client.post<Message>(`/threads/${threadId}/messages`, { role: 'user', content, attachments }).then(r => r.data),
  
  // Files
  uploadFile: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('purpose', 'agents');
    return client.post<FileData>('/files', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(r => r.data);
  },

  // Runs
  createRun: (threadId: string, agentId: string) => 
    client.post<Run>(`/threads/${threadId}/runs`, { agent_id: agentId }).then(r => r.data),
    
  getRun: (threadId: string, runId: string) => client.get<Run>(`/threads/${threadId}/runs/${runId}`).then(r => r.data),

  // Workflows
  getWorkflows: () => client.get<{ workflows: string[] }>('/workflows').then(r => r.data),
  executeWorkflow: (workflowName: string, inputs: Record<string, any>) => 
    client.post<import('../types').WorkflowExecution>(`/workflows/${workflowName}/execute`, { inputs }).then(r => r.data),
  approveWorkflow: (executionId: string) =>
    client.post<import('../types').WorkflowExecution>(`/workflows/executions/${executionId}/approve`).then(r => r.data),
  getWorkflowExecution: (executionId: string) => 
    client.get<import('../types').WorkflowExecution>(`/workflows/executions/${executionId}`).then(r => r.data),
  deleteWorkflowExecution: (executionId: string) => client.delete(`/workflows/executions/${executionId}`).then(r => r.data),
  getWorkflowExecutions: () => 
    client.get<import('../types').WorkflowExecution[]>('/workflows/executions').then(r => r.data),
};
