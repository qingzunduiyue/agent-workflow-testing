// src/hooks/useAgentChat.ts
import { useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { ChatMessage, AgentResponse } from '../types/schema';

// 确保端口对齐你的 FastAPI
const API_BASE_URL = '';

export const useAgentChat = (sessionId: string) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userMsg: ChatMessage = { id: uuidv4(), role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    try {
      // 1. 【入参洗牌】：把前端的文本包装成后端 Pydantic 需要的 message 字段
      const requestPayload = {
        message: text,         // 完美对齐后端 ChatRequest.message
        session_id: sessionId  // 完美对齐后端 ChatRequest.session_id
      };

      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        throw new Error(`HTTP 请求失败，状态码: ${response.status}`);
      }

      // 拿到后端返回的原始字典: { status, plugin_used, reply }
      const rawData = await response.json();

      // 2. 【出参洗牌】：把后端的字段名，翻译成前端 Router Node 认识的 AgentResponse 契约
      const mappedData: AgentResponse = {
        session_id: sessionId,
        user_input: text,
        // 对齐后端的 plugin_used
        plugin_name: rawData.plugin_used || 'unknown',
        // Preserve the backend guardrail result for the warning renderer.
        is_safe: rawData.is_safe !== false,
        risk_reason: rawData.risk_reason ?? null,
        // 对齐后端的 reply (为了防止 reply 是一个嵌套的字典导致 React 崩溃，做一层安全转换)
        final_response: typeof rawData.reply === 'string' ? rawData.reply : JSON.stringify(rawData.reply, null, 2)
      };

      const agentMsg: ChatMessage = {
        id: uuidv4(),
        role: 'agent',
        content: mappedData.final_response,
        state: mappedData, // 携带规范化后的状态流转给 UI 容器
      };

      setMessages(prev => [...prev, agentMsg]);
    } catch (error) {
      console.error('Agent execution failed:', error);
      setMessages(prev => [...prev, {
        id: uuidv4(),
        role: 'agent',
        content: '系统连接异常，请检查后端运行状态。',
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return { messages, sendMessage, isTyping };
};