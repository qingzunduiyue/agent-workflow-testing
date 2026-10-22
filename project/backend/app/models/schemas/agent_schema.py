# app/models/schemas/agent_schema.py
from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    plugin_name: str = "default"
    session_id: Optional[str] = "test_user_001" # 用于隔离对话记忆

class ChatResponse(BaseModel):
    reply: str