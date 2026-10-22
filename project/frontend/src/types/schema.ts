// src/types/schema.ts

export type PluginType = 'travel_assistant' | 'novel_writer' | 'finance_assistant' | 'unknown';

export interface AgentResponse {
  session_id: string;
  user_input: string;
  plugin_name: PluginType;
  is_safe: boolean;
  risk_reason?: string | null;
  final_response: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  state?: AgentResponse; // agent 角色专有，携带完整的后端状态流
  isLoading?: boolean;
}