import React, { useState, useEffect, useRef } from 'react';
import { api } from './api/client';
import type { Agent, Message, Thread, FileData } from './types';
import Markdown from 'react-markdown';
import { Send, Bot, User, Loader2, MessageSquare, Paperclip, X, FileIcon, Plus, PlusCircle } from 'lucide-react';
import { cn } from './lib/utils';

function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [currentThread, setCurrentThread] = useState<Thread | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  
  // Create Agent State
  const [showCreateAgent, setShowCreateAgent] = useState(false);
  const [newAgent, setNewAgent] = useState({ name: '', model: 'gpt-4o-mini', instructions: '' });
  
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

  useEffect(() => {
    if (currentThread) {
      loadMessages(currentThread.id);
    }
  }, [currentThread]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadMessages = async (threadId: string) => {
    try {
      const msgs = await api.getMessages(threadId);
      setMessages(msgs);
    } catch (error) {
      console.error('Failed to load messages', error);
    }
  };

  const handleSelectAgent = async (agent: Agent) => {
    setSelectedAgent(agent);
    setCurrentThread(null);
    setMessages([]);
    setAttachedFiles([]); // Clear files on agent switch
    setIsLoading(true);
    try {
      // 새로운 대화 스레드 생성
      const thread = await api.createThread();
      setCurrentThread(thread);
    } catch (e) {
      console.error(e);
      alert("Failed to create thread. Check backend connection.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateAgent = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!newAgent.name || !newAgent.instructions) return;
      try {
          const created = await api.createAgent(newAgent);
          setAgents(prev => [...prev, created]);
          setShowCreateAgent(false);
          setNewAgent({ name: '', model: 'gpt-4o-mini', instructions: '' });
          handleSelectAgent(created);
      } catch (error) {
          console.error("Failed to create agent", error);
          alert("Failed to create agent");
      }
  };

  const handleNewChat = () => {
    if (selectedAgent) {
        handleSelectAgent(selectedAgent);
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

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setIsUploading(true);
      try {
        const uploaded = await api.uploadFile(file);
        setAttachedFiles(prev => [...prev, uploaded]);
      } catch (err) {
        console.error("File upload failed", err);
        alert("File upload failed");
      } finally {
        setIsUploading(false);
        // Reset input so same file can be selected again
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
    const attachments = attachedFiles.map(f => f.id);
    
    setInput('');
    setAttachedFiles([]); // Clear attachments
    setIsSending(true);

    try {
      // 1. 사용자 메시지 전송 (첨부파일 포함)
      const userMsg = await api.createMessage(currentThread.id, content, attachments);
      setMessages(prev => [...prev, userMsg]);

      // 2. 에이전트 실행 (Run) 요청
      const run = await api.createRun(currentThread.id, selectedAgent.id);

      // 3. 상태 확인 (Polling)
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
             let errorMessage = "Agent run failed or cancelled";
             if (runStatus.last_error && runStatus.last_error.message) {
                errorMessage += `\nReason: ${runStatus.last_error.message}`;
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

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar: Agents List */}
      <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
            <Bot className="w-6 h-6 text-blue-600" />
            Agent Chat
          </h1>
          <button onClick={() => setShowCreateAgent(!showCreateAgent)} className="p-1 hover:bg-gray-200 rounded text-gray-600" title="Create Agent">
            <Plus className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          
          {showCreateAgent ? (
             <form onSubmit={handleCreateAgent} className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm space-y-3 mb-4">
                <h3 className="text-sm font-semibold text-gray-700">New Agent</h3>
                <input 
                  className="w-full text-sm border p-2 rounded" 
                  placeholder="Name" 
                  value={newAgent.name}
                  onChange={e => setNewAgent({...newAgent, name: e.target.value})}
                  required
                />
                <input 
                  className="w-full text-sm border p-2 rounded" 
                  placeholder="Model (e.g. gpt-4o-mini)" 
                  value={newAgent.model}
                  onChange={e => setNewAgent({...newAgent, model: e.target.value})}
                  required
                />
                <p className="text-xs text-gray-500 px-1">
                  * Must match your Azure AI Project deployment name
                </p>
                <textarea 
                  className="w-full text-sm border p-2 rounded" 
                  placeholder="Instructions" 
                  rows={2}
                  value={newAgent.instructions}
                  onChange={e => setNewAgent({...newAgent, instructions: e.target.value})}
                  required
                />
                <div className="flex gap-2">
                   <button type="submit" className="flex-1 bg-blue-600 text-white text-xs py-2 rounded hover:bg-blue-700">Create</button>
                   <button type="button" onClick={() => setShowCreateAgent(false)} className="flex-1 bg-gray-100 text-gray-600 text-xs py-2 rounded hover:bg-gray-200">Cancel</button>
                </div>
             </form>
          ) : (
            <div className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">Agents</div>
          )}

          {agents.map(agent => (
            <button
              key={agent.id}
              onClick={() => handleSelectAgent(agent)}
              className={cn(
                "w-full text-left p-3 rounded-lg text-sm transition-colors flex items-center gap-3",
                selectedAgent?.id === agent.id 
                  ? "bg-blue-100 text-blue-900 ring-1 ring-blue-200" 
                  : "hover:bg-gray-100 text-gray-700"
              )}
            >
              <div className="w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-600">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <div className="font-medium">{agent.name}</div>
                <div className="text-xs text-gray-500 truncate max-w-[120px]">{agent.model}</div>
              </div>
            </button>
          ))}
          
          {agents.length === 0 && !showCreateAgent && (
            <div className="text-sm text-gray-400 text-center py-4 flex flex-col items-center gap-2">
               No agents found.
               <button onClick={() => setShowCreateAgent(true)} className="text-blue-600 text-xs hover:underline">
                 Create your first agent
               </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {selectedAgent ? (
          <>
            {/* Thread Header */}
            <div className="h-16 border-b border-gray-200 flex items-center justify-between px-6 bg-white shrink-0">
               <div className="flex items-center">
                  <h2 className="font-semibold text-gray-800">{selectedAgent.name}</h2>
                  <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{selectedAgent.model}</span>
               </div>
               <button 
                onClick={handleNewChat}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
               >
                 <PlusCircle className="w-4 h-4" />
                 New Chat
               </button>
            </div>

            {/* Messages List */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50/50">
              {isLoading ? (
                 <div className="flex h-full items-center justify-center text-gray-400">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" /> Creating thread...
                 </div>
              ) : messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4">
                  <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center">
                    <MessageSquare className="w-6 h-6 text-gray-300" />
                  </div>
                  <p>Start a conversation with {selectedAgent.name}</p>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={cn(
                      "flex gap-4 max-w-3xl mx-auto",
                      msg.role === 'user' ? "flex-row-reverse" : "flex-row"
                    )}
                  >
                    <div className={cn(
                      "w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1",
                      msg.role === 'user' ? "bg-gray-800" : "bg-blue-600"
                    )}>
                      {msg.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
                    </div>
                    <div className={cn(
                      "rounded-2xl px-5 py-3 text-sm shadow-sm",
                      msg.role === 'user' 
                        ? "bg-gray-800 text-white rounded-tr-sm" 
                        : "bg-white border border-gray-100 text-gray-800 rounded-tl-sm"
                    )}>
                      <Markdown className="prose prose-sm max-w-none dark:prose-invert">
                        {renderMessageContent(msg.content)}
                      </Markdown>
                      {/* Display Attachments if any */}
                      {msg.attachments && msg.attachments.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                           {msg.attachments.map((attId, idx) => (
                              <div key={idx} className="flex items-center gap-1 text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded border border-gray-200 dark:border-gray-600">
                                <FileIcon className="w-3 h-3" />
                                <span>File attachment ({attId.slice(0, 4)}...)</span>
                              </div>
                           ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              {isSending && (
                 <div className="flex gap-4 max-w-3xl mx-auto animate-pulse">
                    <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0 mt-1">
                       <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-5 py-3 h-10 w-16" />
                 </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <div className="p-4 bg-white border-t border-gray-200">
              {attachedFiles.length > 0 && (
                <div className="mb-2 flex flex-wrap gap-2">
                  {attachedFiles.map(file => (
                    <div key={file.id} className="flex items-center gap-2 text-xs bg-blue-50 text-blue-700 px-3 py-1.5 rounded-full border border-blue-100">
                       <FileIcon className="w-3 h-3" />
                       <span className="max-w-[150px] truncate">{file.filename}</span>
                       <button onClick={() => removeFile(file.id)} className="hover:text-red-500"><X className="w-3 h-3" /></button>
                    </div>
                  ))}
                </div>
              )}
              <form onSubmit={handleSendMessage} className="max-w-3xl mx-auto relative flex items-center gap-2">
                 <input 
                   type="file" 
                   ref={fileInputRef} 
                   className="hidden" 
                   onChange={handleFileSelect} 
                 />
                 <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isSending || isLoading || isUploading}
                  className="p-3 bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700 rounded-full transition-colors"
                  title="Attach File"
                 >
                   {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
                 </button>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={attachedFiles.length > 0 ? "Add a message..." : `Message ${selectedAgent.name}...`}
                  disabled={isSending || isLoading}
                  className="flex-1 bg-gray-100 border-0 rounded-full px-5 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all outline-none"
                />
                <button
                  type="submit"
                  disabled={(!input.trim() && attachedFiles.length === 0) || isSending || isLoading}
                  className="p-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-full text-white transition-colors"
                >
                  {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </form>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400 space-y-4">
             <Bot className="w-16 h-16 text-gray-200" />
             <p className="text-lg font-medium text-gray-600">Select an agent to start chatting</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

