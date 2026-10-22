// src/components/layout/ChatContainer.tsx
import React from 'react';
import { ChatMessage } from '../../types/schema';
import { NovelView } from '../plugins/NovelView';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatContainerProps {
  message: ChatMessage;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({ message }) => {
  // 1. 用户气泡渲染保持不变
  if (message.role === 'user') {
    return (
      <div className="flex justify-end my-4 w-full">
        <div className="bg-blue-600 text-white px-5 py-3 rounded-2xl rounded-tr-sm max-w-[70%] shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  const { state } = message;

  // 2. 渲染 Guardrail 拦截警告
  if (state && !state.is_safe) {
    return (
      <div className="flex justify-start my-4 w-full">
        <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded shadow-sm w-full">
          <p className="font-bold flex items-center"><span className="mr-2">🚨</span>拦截警告 (Blocker Node)</p>
          <p className="mt-1">{message.content}</p>
        </div>
      </div>
    );
  }

// 3. 渲染意图路由结果
  const renderPluginView = () => {
    // ==========================================
    // 🧹 新增：Markdown 格式清洗器 (防腐层)
    // 专门修复大模型输出的 "** 文本 **" 等破损格式
    // ==========================================
    const cleanMarkdownFormat = (text: string) => {
      if (!text) return "";
      // 正则解析：将前后带有不规则空格的双星号，强制压缩为紧凑的 **文本**
      return text.replace(/\*\*\s*(.*?)\s*\*\*/g, "**$1**");
    };

    // 通用的 Markdown 渲染组件
    const MarkdownRenderer = ({ content }: { content: string }) => (
      <div className="bg-white border border-gray-100 px-6 py-5 rounded-2xl rounded-tl-sm shadow-sm w-full">
        <div className="prose prose-slate prose-a:text-blue-600 max-w-none w-full">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content}
          </ReactMarkdown>
        </div>
      </div>
    );

    // 如果没有 state，说明可能是底层框架的纯文本反馈，清洗后直接渲染
    if (!state) {
      return <MarkdownRenderer content={cleanMarkdownFormat(message.content)} />;
    }

    // ==========================================
    // 🔒 核心修改点：在向下游组件派发前，全局清洗一次数据！
    // ==========================================
    const cleanedResponse = cleanMarkdownFormat(state.final_response);

    switch (state.plugin_name) {
      case 'novel_writer':
        // 现在的 NovelView 拿到的一定是 100% 格式正确的 Markdown 文本了
        return <NovelView content={cleanedResponse} />;
      case 'travel_assistant':
        return <MarkdownRenderer content={cleanedResponse} />;
      case 'finance_assistant':
        return <MarkdownRenderer content={cleanedResponse} />;
      default:
        // 通用兜底渲染
        return <MarkdownRenderer content={cleanedResponse} />;
    }
  };

  return (
    <div className="flex justify-start my-4 w-full">
      {renderPluginView()}
    </div>
  );
};