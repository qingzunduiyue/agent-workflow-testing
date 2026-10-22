# app/api/router.py
from fastapi import APIRouter
from app.models.schemas.agent_schema import ChatRequest, ChatResponse
from app.engine.agent_executor import run_agent

api_router = APIRouter()

@api_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # 调用核心执行器
    reply = await run_agent(request.message, request.plugin_name)
    return ChatResponse(reply=reply)