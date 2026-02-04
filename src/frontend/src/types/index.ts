export interface Agent {
  id: string;
  name: string;
  model: string;
  instructions: string;
  tools: string[];
  created_at: number;
}

export interface AgentCreate {
  name: string;
  model: string;
  instructions: string;
}

export interface Thread {
  id: string;
  metadata: Record<string, any>;
  created_at: number;
}


export interface Message {
  id: string;
  thread_id: string;
  role: 'user' | 'assistant';
  content: string | any[];
  attachments?: { id: string; type: string }[];
  created_at: number;
}

export interface FileData {
  id: string;
  filename: string;
  purpose: string;
  mime_type: string;
  created_at: number;
}

export interface Run {
  id: string;
  thread_id: string;
  agent_id: string;
  status: 'queued' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  created_at: number;
  last_error?: any;
}

export interface WorkflowExecution {
  execution_id: string;
  workflow_name: string;
  status: 'queued' | 'running' | 'in_progress' | 'completed' | 'failed' | 'waiting_for_approval';
  result?: {
    plan?: string;
    steps: Array<{
      agent: string;
      action: string;
      details: string;
      timestamp: number;
    }>;
  };
  inputs?: Record<string, any>;
  created_at: number;
}

export interface WorkflowInput {
  inputs: Record<string, any>;
}
