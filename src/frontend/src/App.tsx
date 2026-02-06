import React, { useState, useEffect, useRef } from 'react';
import { api } from './api/client';
import type { Agent, Message, Thread, FileData, WorkflowExecution } from './types';
import Markdown from 'react-markdown';
import { Send, Bot, User, Loader2, MessageSquare, Paperclip, X, FileIcon, Plus, PlusCircle, Play, CheckCircle2, Clock, Trash2 } from 'lucide-react';
import { cn } from './lib/utils';

const MCP_EXAMPLES: Record<string, string[]> = {
  'mcp-hr-policy': ['emp_001 직원의 남은 휴가는?', 'emp_001의 휴가 신청 내역 조회해줘'],
  'mcp-sales-crm': ['태산 물산의 최근 활동 내역 보여줘', '태산 물산의 리스크 점수는?'],
  'mcp-supply-chain': ['WIDGET-X100 제품 재고 알려줘', '재고 부족한 상품 있어?'],
  'mcp-weather': ['서울 날씨 어때?', '부산 날씨 알려줘']
};

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'workflow'>('chat');
  
  // Chat State
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [currentThread, setCurrentThread] = useState<Thread | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  
  // Workflow State
  const [workflowName, setWorkflowName] = useState('hr-onboarding');
  const [wfInputName, setWfInputName] = useState('');
  const [wfInputRole, setWfInputRole] = useState('');
  const [currentExecution, setCurrentExecution] = useState<WorkflowExecution | null>(null);
  const [isExecutingWf, setIsExecutingWf] = useState(false);
  const [workflowHistory, setWorkflowHistory] = useState<WorkflowExecution[]>([]);

  // Create Agent State
  const [showCreateAgent, setShowCreateAgent] = useState(false);
  const [newAgent, setNewAgent] = useState<{name: string, model: string, instructions: string, mcp_tools: string[]}>({ 
    name: '', model: 'gpt-4o-mini', instructions: '', mcp_tools: [] 
  });
  
  const mcpOptions = [
    { id: 'mcp-hr-policy', label: 'HR (인사)', desc: "휴가 조회/신청" },
    { id: 'mcp-sales-crm', label: 'Sales (매출)', desc: "고객/주문 데이터" },
    { id: 'mcp-supply-chain', label: 'Supply (재고)', desc: "재고 확인" },
    { id: 'mcp-weather', label: 'Weather (날씨)', desc: "날씨 조회" },
  ];

  const handleMcpChange = (mcpId: string, checked: boolean) => {
    setNewAgent(prev => {
      // Single selection mode: If checked, replace all with new one. If unchecked, clear it.
      const updatedTools = checked 
        ? [mcpId]
        : [];
      
      return { ...prev, mcp_tools: updatedTools };
    });
  };
  
  // File upload state
  const [isUploading, setIsUploading] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<FileData[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 백엔드 연결 실패 시 에러 처리 추가
    api.getAgents()
      .then(setAgents)
      .catch(err => {
        console.error("Failed to fetch agents:", err);
      });
  }, []);

  // Poll for workflow status
  useEffect(() => {
    let interval: any;
    if (currentExecution && isExecutingWf) {
      interval = setInterval(async () => {
        try {
          const updated = await api.getWorkflowExecution(currentExecution.execution_id);
          setCurrentExecution(updated);
          if (updated.status === 'completed' || updated.status === 'failed') {
            setIsExecutingWf(false);
            loadWorkflowHistory();
          } else if (updated.status === 'waiting_for_approval') {
            setIsExecutingWf(false); // Stop loading spinner, waiting for user
          }
        } catch (e) {
          console.error(e);
          setIsExecutingWf(false);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [currentExecution, isExecutingWf]);

  useEffect(() => {
    if (activeTab === 'workflow') {
      loadWorkflowHistory();
    }
  }, [activeTab]);

  const loadWorkflowHistory = async () => {
    try {
      const history = await api.getWorkflowExecutions();
      // Sort by created_at descending if available, else reverse list (assuming backend returns oldest first)
      history.sort((a, b) => (b.created_at || 0) - (a.created_at || 0));
      setWorkflowHistory(history);
    } catch (e) {
      console.error("Failed to load workflow history", e);
    }
  };

  useEffect(() => {
    if (currentThread) {
      loadMessages(currentThread.id);
    }
  }, [currentThread]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    if (activeTab === 'chat') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const loadMessages = async (threadId: string) => {
    try {
      const msgs = await api.getMessages(threadId);
      setMessages(msgs.reverse());
    } catch (error) {
      console.error('Failed to load messages', error);
    }
  };

  const handleDeleteAgent = async (agentId: string) => {
    if (!window.confirm("정말로 이 에이전트를 삭제하시겠습니까? (복구 불가)")) return;
    try {
        await api.deleteAgent(agentId);
        setAgents(prev => prev.filter(a => a.id !== agentId));
        if (selectedAgent?.id === agentId) {
            setSelectedAgent(null);
            setCurrentThread(null);
            setMessages([]);
        }
    } catch (e) {
        console.error("Failed to delete agent", e);
        alert("에이전트 삭제 실패");
    }
  };

  const handleSelectAgent = async (agent: Agent) => {
    setSelectedAgent(agent);
    setCurrentThread(null);
    setMessages([]);
    setAttachedFiles([]); // Clear files on agent switch
    setIsLoading(true);
    try {
      // 1. Check if there is a saved thread for this agent
      const saved = await api.getAgentThread(agent.id);
      
      if (saved.thread_id) {
         // 2. Resume existing thread
         setCurrentThread({ id: saved.thread_id, metadata: {}, created_at: Date.now() }); // Reconstruction minimal obj
         await loadMessages(saved.thread_id);
      } else {
         // 3. Create new thread and save it
         const thread = await api.createThread();
         setCurrentThread(thread);
         await api.setAgentThread(agent.id, thread.id);
      }
    } catch (e) {
      console.error(e);
      // Fallback: Just create new if fetch fails? Or alert?
      // Let's try to create new if get fails to be robust
      try {
        const thread = await api.createThread();
        setCurrentThread(thread);
      } catch (inner) {
          alert("스레드 생성 실패. 백엔드 연결을 확인하세요.");
      }
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleDeleteWorkflowExecution = async (executionId: string) => {
      if (!window.confirm("이 워크플로우 실행 기록을 삭제하시겠습니까?")) return;
      try {
          await api.deleteWorkflowExecution(executionId);
          setWorkflowHistory(prev => prev.filter(e => e.execution_id !== executionId));
          if (currentExecution?.execution_id === executionId) {
              setCurrentExecution(null);
          }
      } catch (e) {
          console.error("Failed to delete workflow execution", e);
          alert("삭제 실패");
      }
  };

  const handleCreateAgent = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!newAgent.name || !newAgent.instructions) return;
      try {
          const created = await api.createAgent(newAgent);
          setAgents(prev => [...prev, created]);
          setShowCreateAgent(false);
          setNewAgent({ name: '', model: 'gpt-4o-mini', instructions: '', mcp_tools: [] });
          handleSelectAgent(created);
      } catch (error) {
          console.error("Failed to create agent", error);
          alert("에이전트 생성 실패");
      }
  };

  const handleStartWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!wfInputName || !wfInputRole) return;
    
    setIsExecutingWf(true);
    setCurrentExecution(null);
    try {
      const exec = await api.executeWorkflow(workflowName, {
        name: wfInputName,
        role: wfInputRole
      });
      setCurrentExecution(exec);
    } catch (e) {
      console.error(e);
      alert("워크플로우 시작 실패");
      setIsExecutingWf(false);
    }
  };
  
  const handleApproveWorkflow = async () => {
    if (!currentExecution) return;
    
    setIsExecutingWf(true);
    try {
        const exec = await api.approveWorkflow(currentExecution.execution_id);
        setCurrentExecution(exec);
    } catch (e) {
        console.error("Failed to approve workflow", e);
        alert("승인 실패");
        setIsExecutingWf(false);
    }
  };

  const handleCreateNewWorkflow = () => {
    setCurrentExecution(null);
    setWfInputName('');
    setWfInputRole('');
    setIsExecutingWf(false);
  };

  const handleNewChat = () => {
    if (selectedAgent) {
        handleSelectAgent(selectedAgent);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setIsUploading(true);
      try {
        const uploaded = await api.uploadFile(file);
        setAttachedFiles(prev => [...prev, uploaded]);
      } catch (err) {
        console.error("File upload failed", err);
        alert("파일 업로드 실패");
      } finally {
        setIsUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    }
  };

  const removeFile = (fileId: string) => {
    setAttachedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && attachedFiles.length === 0) || !currentThread || !selectedAgent) return;

    const content = input;
    const attachments = attachedFiles.map(f => ({ id: f.id, type: f.mime_type }));
    setInput('');
    setAttachedFiles([]); 
    setIsSending(true);

    try {
      const userMsg = await api.createMessage(currentThread.id, content, attachments);
      setMessages(prev => [...prev, userMsg]);

      const run = await api.createRun(currentThread.id, selectedAgent.id);

      const pollInterval = setInterval(async () => {
        try {
          const runStatus = await api.getRun(currentThread.id, run.id);
          if (runStatus.status === 'completed') {
            clearInterval(pollInterval);
            setIsSending(false);
            await loadMessages(currentThread.id);
          } else if (runStatus.status === 'failed' || runStatus.status === 'cancelled') {
             clearInterval(pollInterval);
             setIsSending(false);
             let errorMessage = "에이전트 실행이 실패하거나 취소되었습니다.";
             if (runStatus.last_error && runStatus.last_error.message) {
                errorMessage += `\n사유: ${runStatus.last_error.message}`;
             }
             alert(errorMessage);
             return;
          }
        } catch (e) {
          clearInterval(pollInterval);
          setIsSending(false);
          console.error(e);
        }
      }, 1000);
    } catch (error) {
       console.error("Error sending message", error);
       setIsSending(false);
    }
  };

  const renderMessageContent = (content: any) => {
    if (typeof content === 'string') return content;
    if (Array.isArray(content)) {
      return content.map((c: any) => {
        if (c.type === 'text') return c.text?.value || '';
        return '';
      }).join('\n');
    }
    return JSON.stringify(content);
  };

  const renderWorkflowTab = () => (
    <div className="flex-1 flex flex-col h-full bg-gray-50 p-6 overflow-hidden">
      <div className="max-w-4xl mx-auto w-full h-full flex flex-col gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Bot className="w-6 h-6 text-blue-600" />
            HR 온보딩 워크플로우
          </h2>
          <p className="text-gray-500 text-sm">
            멀티 에이전트 프로세스 시뮬레이션: 계정 생성 &rarr; 자산 할당 &rarr; 교육 배정 &rarr; 완료
          </p>
          
          <form onSubmit={handleStartWorkflow} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">지원자 이름</label>
              <input 
                type="text" 
                value={wfInputName}
                onChange={e => setWfInputName(e.target.value)}
                placeholder="예: 홍길동"
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">직군 / 포지션</label>
              <input 
                type="text" 
                value={wfInputRole}
                onChange={e => setWfInputRole(e.target.value)}
                placeholder="예: 시니어 개발자"
                className="w-full px-3 py-2 border rounded-md"
                required
              />
            </div>
            <div className="flex items-end">
              <button 
                type="submit"
                disabled={isExecutingWf && currentExecution?.status !== 'completed' && currentExecution?.status !== 'failed'}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isExecutingWf && currentExecution?.status !== 'completed' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    처리 중...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    온보딩 시작
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {currentExecution && (
          <div className="bg-white p-6 rounded-lg shadow-sm border flex-1 overflow-auto">
            <h3 className="text-lg font-medium mb-4 flex items-center justify-between">
              <span>
                진행 상태: <span className={cn("capitalize", 
                  currentExecution.status === 'completed' ? 'text-green-600' : 
                  currentExecution.status === 'failed' ? 'text-red-600' : 'text-blue-600'
                )}>{currentExecution.status === 'waiting_for_approval' ? '승인 대기 중' : currentExecution.status}</span>
              </span>
              <span className="text-xs text-gray-400 font-normal">ID: {currentExecution.execution_id}</span>
            </h3>

            {currentExecution.status === 'waiting_for_approval' && currentExecution.result?.plan && (
                <div className="mb-6 bg-yellow-50 border border-yellow-200 p-4 rounded-md">
                    <h4 className="font-semibold text-yellow-800 mb-2">실행 계획 (승인 필요)</h4>
                    <div className="prose prose-sm max-w-none text-gray-700 mb-4 bg-white p-3 rounded border border-yellow-100 text-xs leading-relaxed">
                        <Markdown>{currentExecution.result.plan}</Markdown>
                    </div>
                    <div className="flex gap-3">
                        <button 
                            onClick={handleApproveWorkflow}
                            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md font-medium text-sm flex items-center gap-2"
                        >
                            <CheckCircle2 className="w-4 h-4" />
                            계획 승인 및 실행
                        </button>
                         <button 
                            onClick={handleCreateNewWorkflow}
                            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-md font-medium text-sm"
                        >
                            취소
                        </button>
                    </div>
                </div>
            )}

            <div className="space-y-6 relative pl-4 border-l-2 border-gray-100 ml-4">
              {currentExecution.result?.steps?.map((step, idx) => (
                <div key={idx} className="relative">
                  {/* Icon aligned with the first line of text (Agent Name) inside the card (p-4 = 1rem = 16px top padding) */}
                  {/* Agent name is text-base/font-semibold (line-height ~24px). Center is ~12px + 16px = 28px. */}
                  {/* Icon is 16px height. Center is 8px + top. To match 28px, top should be 20px (top-5). */}
                  <span className="absolute -left-[21px] top-5 w-4 h-4 rounded-full bg-blue-100 border-2 border-blue-600 flex items-center justify-center bg-white z-10">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                  </span>
                  <div className="bg-gray-50 p-4 rounded-md border shadow-sm">
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-semibold text-gray-900">{step.agent}</span>
                      <span className="text-xs text-gray-500 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date((step.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-sm font-medium text-blue-700 mb-1">{step.action}</div>
                    <div className="text-sm text-gray-600 whitespace-pre-wrap">
                        {step.details.replace(/\*\*/g, '')}
                    </div>
                  </div>
                </div>
              ))}
              
              {currentExecution.status === 'in_progress' && (
                <div className="relative flex items-center h-8">
                   <span className="absolute -left-[21px] w-4 h-4 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center bg-white z-10">
                    <Loader2 className="w-3 h-3 animate-spin text-gray-500" />
                  </span>
                  <div className="text-sm text-gray-500 italic pl-2">다음 단계 진행 중...</div>
                </div>
              )}
               {currentExecution.status === 'completed' && (
                <div className="relative flex items-center h-8">
                   <span className="absolute -left-[21px] w-4 h-4 rounded-full bg-green-100 border-2 border-green-600 flex items-center justify-center bg-white z-10">
                    <CheckCircle2 className="w-3 h-3 text-green-600" />
                  </span>
                  <div className="text-sm text-green-600 font-medium pl-2">워크플로우가 성공적으로 완료되었습니다.</div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-72 bg-gray-900 text-white flex flex-col border-r border-gray-800">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <span className="bg-blue-600 w-8 h-8 rounded flex items-center justify-center">AI</span>
            에이전트 플랫폼
          </h1>
        </div>
        
         <div className="px-3 py-4 space-y-1">
           <div className={cn("group w-full flex items-center gap-1 rounded-md transition-colors pr-2", 
              activeTab === 'chat' ? "bg-gray-800 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800/50"
            )}>
              <button 
                onClick={() => setActiveTab('chat')}
                className="flex-1 text-left px-3 py-2 flex items-center gap-2"
              >
                <MessageSquare className="w-4 h-4" />
                에이전트 채팅
              </button>
               <button 
                 onClick={(e) => { e.stopPropagation(); setActiveTab('chat'); setShowCreateAgent(true); }}
                 className="p-1.5 rounded-md hover:bg-gray-700 text-gray-400 hover:text-white transition-all"
                 title="새 에이전트 생성"
               >
                  <Plus className="w-4 h-4" />
               </button>
          </div>

          <div className={cn("group w-full flex items-center gap-1 rounded-md transition-colors pr-2", 
              activeTab === 'workflow' ? "bg-gray-800 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800/50"
            )}>
              <button 
                onClick={() => setActiveTab('workflow')}
                className="flex-1 text-left px-3 py-2 flex items-center gap-2"
              >
                <Bot className="w-4 h-4" />
                워크플로우
              </button>
               <button 
                 onClick={(e) => { e.stopPropagation(); setActiveTab('workflow'); handleCreateNewWorkflow(); }}
                 className="p-1.5 rounded-md hover:bg-gray-700 text-gray-400 hover:text-white transition-all"
                 title="새 워크플로우 시작"
               >
                  <Plus className="w-4 h-4" />
               </button>
          </div>
        </div>

        {activeTab === 'chat' ? (
          <div className="flex-1 overflow-y-auto px-3 pb-4">
             <div className="flex items-center justify-between mb-2 mt-4 px-1">
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">에이전트 목록</h2>
            </div>
            
            <div className="space-y-1">
              {agents.map(agent => (
                <div
                  key={agent.id}
                  className={cn(
                    "group/item w-full flex items-center pr-2 rounded-md transition-colors",
                    selectedAgent?.id === agent.id ? "bg-blue-600/10" : "hover:bg-gray-800"
                  )}
                >
                  <button
                    onClick={() => handleSelectAgent(agent)}
                    className={cn(
                      "flex-1 text-left px-3 py-3 rounded-md flex items-center gap-3 overflow-hidden",
                      selectedAgent?.id === agent.id ? "text-blue-400" : "text-gray-300"
                    )}
                  >
                    <Bot className="w-5 h-5 shrink-0" />
                    <div className="truncate w-full">
                      <div className="font-medium text-sm truncate">{agent.name}</div>
                      <div className="text-xs opacity-70 truncate">{agent.model}</div>
                      <div className="text-[10px] opacity-50 truncate" title={agent.id}>ID: {agent.id}</div> 
                    </div>
                  </button>
                   <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteAgent(agent.id); }}
                        className="p-2 rounded-md hover:bg-red-500/20 text-gray-500 hover:text-red-400 opacity-0 group-hover/item:opacity-100 transition-all shrink-0"
                        title="에이전트 삭제"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
              ))}
            </div>
            
            {agents.length === 0 && (
                <div className="text-sm text-gray-500 px-2 py-4 text-center border-dashed border border-gray-700 rounded-md m-2">
                    에이전트가 없습니다.<br/>새로 생성해주세요.
                </div>
            )}
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto px-3 pb-4">
             <div className="flex items-center justify-between mb-2 mt-4 px-1">
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">히스토리</h2>
            </div>
            
            <div className="space-y-1">
              {workflowHistory.map(exec => (
                <div 
                    key={exec.execution_id}
                    className={cn(
                        "group/item w-full flex items-center pr-2 rounded-md transition-colors",
                         currentExecution?.execution_id === exec.execution_id ? "bg-blue-600/10" : "hover:bg-gray-800"
                    )}
                >
                    <button
                    onClick={() => setCurrentExecution(exec)}
                    className={cn(
                        "flex-1 text-left px-3 py-3 rounded-md transition-colors flex items-center gap-3 overflow-hidden",
                        currentExecution?.execution_id === exec.execution_id ? "text-blue-400" : "text-gray-300"
                    )}
                    >
                    <div className={cn("w-2 h-2 rounded-full shrink-0", 
                        exec.status === 'completed' ? "bg-green-400" : 
                        exec.status === 'failed' ? "bg-red-400" : "bg-blue-400 animate-pulse"
                    )} />
                    <div className="truncate w-full">
                        <div className="font-medium text-sm truncate">
                          {exec.workflow_name === 'hr-onboarding' && exec.inputs?.name 
                            ? `${exec.inputs.name} 온보딩 처리` 
                            : ((exec.result?.steps?.[0]?.details?.split(': ')?.[1]) || exec.execution_id.slice(0, 8))}
                        </div>
                        <div className="text-xs opacity-70 truncate capitalize">{exec.status}</div>
                    </div>
                    </button>
                    <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteWorkflowExecution(exec.execution_id); }}
                        className="p-2 rounded-md hover:bg-red-500/20 text-gray-500 hover:text-red-400 opacity-0 group-hover/item:opacity-100 transition-all shrink-0"
                        title="기록 삭제"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
              ))}
            </div>
             {workflowHistory.length === 0 && (
                <div className="text-sm text-gray-500 px-2 py-4 text-center border-dashed border border-gray-700 rounded-md m-2">
                    실행 이력이 없습니다.
                </div>
            )}
          </div>
        )}
        
        <div className="p-4 border-t border-gray-800 text-xs text-gray-500">
          에이전트 프레임워크 샘플
        </div>
      </div>

      {activeTab === 'chat' ? (
        <div className="flex-1 flex flex-col h-full bg-white relative">
          {selectedAgent ? (
             <>
              <div className="h-16 border-b flex items-center justify-between px-6 bg-white shrink-0 z-10">
                <div>
                  <h2 className="font-semibold text-gray-800 flex items-center gap-2">
                    <Bot className="w-5 h-5 text-blue-600" />
                    {selectedAgent.name}
                  </h2>
                  <p className="text-xs text-gray-500 max-w-[400px] truncate">{selectedAgent.instructions}</p>
                </div>
                <div className='flex gap-2'>
                    <button 
                        onClick={handleNewChat}
                        className='px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-md flex items-center gap-1.5'
                    >
                        <PlusCircle className='w-4 h-4'/>
                        새 대화
                    </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50 scroll-smooth">
                {messages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4">
                    <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center">
                        <Bot className="w-8 h-8 text-gray-400" />
                    </div>
                    <p>{selectedAgent.name}와 대화를 시작하세요</p>
                  </div>
                ) : (
                  messages.map((msg, idx) => (
                    <div 
                      key={msg.id || idx} 
                      className={cn(
                        "flex gap-4 max-w-3xl mx-auto",
                        msg.role === 'user' ? "flex-row-reverse" : "flex-row"
                      )}
                    >
                      <div className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                        msg.role === 'user' ? "bg-gray-900 text-white" : "bg-blue-100 text-blue-600"
                      )}>
                        {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                      </div>
                      <div className={cn(
                        "rounded-2xl px-5 py-3.5 max-w-[80%] shadow-sm text-sm leading-relaxed",
                        msg.role === 'user' 
                          ? "bg-gray-900 text-white rounded-tr-none" 
                          : "bg-white border border-gray-100 text-gray-800 rounded-tl-none"
                      )}>
                        <Markdown className="prose prose-sm max-w-none break-words dark:prose-invert">
                            {renderMessageContent(msg.content)}
                        </Markdown>
                         {msg.attachments && msg.attachments.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-gray-200/20 space-y-1">
                                {msg.attachments.map((att, i) => (
                                    <div key={i} className="flex items-center gap-2 text-xs bg-black/5 p-1.5 rounded">
                                        <FileIcon className="w-3 h-3" />
                                        <span>파일 ID: {att.id}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                <div ref={messagesEndRef} className='h-1' />
              </div>

              <div className="p-4 bg-white border-t shrink-0">
                <div className="max-w-3xl mx-auto space-y-3">
                    {attachedFiles.length > 0 && (
                        <div className="flex gap-2 overflow-x-auto py-2">
                             {attachedFiles.map(file => (
                                <div key={file.id} className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full text-xs border border-blue-100">
                                    <FileIcon className="w-3 h-3" />
                                    <span className="max-w-[100px] truncate">{file.filename}</span>
                                    <button onClick={() => setAttachedFiles(prev => prev.filter(f => f.id !== file.id))} className="hover:text-blue-900">
                                        <X className="w-3 h-3" />
                                    </button>
                                </div>
                             ))}
                        </div>
                    )}

                  <form onSubmit={handleSendMessage} className="relative flex items-end gap-2 bg-white border rounded-xl shadow-sm p-2 focus-within:ring-2 focus-within:ring-blue-100 focus-within:border-blue-300 transition-all">
                    <button 
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                        title="파일 첨부"
                    >
                        <Paperclip className="w-5 h-5" />
                    </button>
                    <input 
                        type="file" 
                        ref={fileInputRef}
                        className="hidden" 
                        onChange={handleFileSelect}
                    />
                    
                    <textarea 
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage(e);
                        }
                      }}
                      placeholder={isLoading ? "AI가 생각 중입니다..." : selectedAgent.name + "에게 메시지 보내기..."}
                      className="w-full max-h-[120px] py-2.5 px-2 bg-transparent border-none focus:ring-0 resize-none text-sm placeholder:text-gray-400"
                      rows={1}
                      style={{ minHeight: '44px' }}
                      disabled={isLoading || isSending}
                    />

                    <button 
                      type="submit" 
                      disabled={(!input.trim() && attachedFiles.length === 0) || isLoading || isSending}
                      className={cn(
                        "p-2 rounded-lg transition-all duration-200",
                        (input.trim() || attachedFiles.length > 0) && !isLoading && !isSending
                          ? "bg-blue-600 text-white shadow-md hover:bg-blue-700" 
                          : "bg-gray-100 text-gray-300 cursor-not-allowed"
                      )}
                    >
                      {isSending ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Send className="w-5 h-5" />
                      )}
                    </button>
                  </form>

                    {selectedAgent && selectedAgent.mcp_tools && (
                      <div className="flex flex-wrap gap-2 mt-3 mb-1 px-1 justify-center">
                        {selectedAgent.mcp_tools.flatMap(toolId => MCP_EXAMPLES[toolId] || []).map((example, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => setInput(example)}
                            className="text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded-full hover:bg-blue-50 hover:text-blue-600 transition-colors border border-gray-200 hover:border-blue-100 font-medium"
                          >
                            {example}
                          </button>
                        ))}
                      </div>
                    )}

                  <p className="text-center text-xs text-gray-400 mt-2">
                    AI는 실수를 할 수 있습니다. 중요한 정보를 확인하세요.
                  </p>
                </div>
              </div>
            </> 
          ) : (
             <div className="flex-1 flex flex-col items-center justify-center text-gray-400 p-8 text-center"> 
                <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-6">
                    <Bot className="w-10 h-10 text-gray-300" />
                </div>
                <h3 className="text-lg font-semibold text-gray-700 mb-2">에이전트 선택</h3>
                <p className="max-w-md">사이드바에서 에이전트를 선택하거나 새로운 에이전트를 생성하여 작업을 시작하세요.</p>
                <button 
                    onClick={() => setShowCreateAgent(true)}
                    className="mt-6 px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 shadow-md font-medium flex items-center gap-2"
                >
                    <Plus className="w-4 h-4" />
                    새 에이전트 생성
                </button>
             </div>
          )}
        </div>
      ) : (
        renderWorkflowTab()
      )}

      {showCreateAgent && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
                    <h3 className="font-semibold text-gray-800">새 에이전트 생성</h3>
                    <button onClick={() => setShowCreateAgent(false)} className="text-gray-400 hover:text-gray-600">
                        <X className="w-5 h-5" />
                    </button>
                  </div>
                  <form onSubmit={handleCreateAgent} className="p-6 space-y-4">
                      <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">이름</label>
                          <input 
                            required
                            type="text" 
                            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all outline-none"
                            placeholder="예: 데이터 분석가"
                            value={newAgent.name}
                            onChange={e => setNewAgent({...newAgent, name: e.target.value})}
                          />
                      </div>
                      <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">모델</label>
                          <input 
                            type="text" 
                            disabled
                            className="w-full px-3 py-2 border rounded-lg bg-gray-100 text-gray-500 cursor-not-allowed"
                            value={newAgent.model} 
                          />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">MCP 도구 연결 (선택)</label>
                        <div className="grid grid-cols-2 gap-2">
                          {mcpOptions.map(opt => (
                            <label key={opt.id} className="flex items-start gap-2 p-2 border rounded-lg hover:bg-gray-50 cursor-pointer">
                              <input 
                                type="checkbox"
                                checked={newAgent.mcp_tools?.includes(opt.id) || false}
                                onChange={(e) => handleMcpChange(opt.id, e.target.checked)}
                                className="mt-1"
                              />
                              <div>
                                <div className="text-sm font-medium text-gray-800">{opt.label}</div>
                                <div className="text-xs text-gray-500">{opt.desc}</div>
                              </div>
                            </label>
                          ))}
                        </div>
                      </div>

                      <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">지침 (페르소나)</label>
                          <textarea 
                             required
                             className="w-full px-3 py-2 border rounded-lg h-32 resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all outline-none"
                             placeholder="당신은 유능한 어시스턴트입니다..."
                             value={newAgent.instructions}
                             onChange={e => setNewAgent({...newAgent, instructions: e.target.value})}
                          />
                      </div>
                      <div className="pt-2">
                        <button type="submit" className="w-full bg-blue-600 text-white py-2.5 rounded-lg hover:bg-blue-700 font-medium shadow-sm transition-colors">
                            에이전트 생성
                        </button>
                      </div>
                  </form>
              </div>
          </div>
      )}
    </div>
  );
}

export default App;
