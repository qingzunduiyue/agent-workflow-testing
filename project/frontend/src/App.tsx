// src/App.tsx
import React, { useState, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAgentChat } from './hooks/useAgentChat';
import { ChatContainer } from './components/layout/ChatContainer';

// 固化一个 session_id 用于测试 LangGraph 记忆节点
const TEST_SESSION_ID = uuidv4();

function App() {
  const { messages, sendMessage, isTyping } = useAgentChat(TEST_SESSION_ID);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 监听消息变化，自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isTyping) return;
    sendMessage(inputValue);
    setInputValue('');
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 font-sans">
      {/* 顶部导航区 */}
      <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
        <h1 className="text-xl font-bold text-gray-800 flex items-center">
          <span className="text-blue-600 mr-2">⚛️</span>
          多场景 Agent · 交互演示
        </h1>
        <div className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
          Session: {TEST_SESSION_ID.slice(0, 8)}
        </div>
      </header>

      {/* 核心对话 / 渲染区 */}
      <main className="flex-grow overflow-y-auto p-6 max-w-6xl mx-auto w-full">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-400">
            <p className="text-lg font-medium text-gray-500">底层引擎已就绪，请输入指令触发多态路由...</p>
            <p className="text-sm mt-2">默认使用本地演示模式，输出固定示例，不调用模型。配置真实模型后可自由对话。</p>
          </div>
        ) : (
          messages.map((msg) => <ChatContainer key={msg.id} message={msg} />)
        )}

        {/* 全局 Loading 状态 */}
        {isTyping && (
          <div className="flex justify-start my-4">
            <div className="bg-white border border-gray-200 px-5 py-3 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              <span className="ml-2 text-sm text-gray-500">Agent Executor 状态机流转中...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* 底部输入控制台 */}
      <footer className="bg-white border-t border-gray-200 p-4">
        <form onSubmit={handleSend} className="max-w-6xl mx-auto flex gap-3">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isTyping}
            placeholder="输入触发意图的内容..."
            className="flex-grow px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={isTyping || !inputValue.trim()}
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            发送
          </button>
        </form>
      </footer>
    </div>
  );
}

export default App;