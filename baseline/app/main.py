# app/main.py

from fastapi import FastAPI
from pydantic import BaseModel, Field
from app.engine.router import classify_intent
from app.engine.agent_executor import run_agent
from fastapi.middleware.cors import CORSMiddleware

# 1. 初始化 FastAPI 实例 (Uvicorn 依赖这个 app)
app = FastAPI(
    title="Multi-Scenario Agent Framework",
    description="工业级多场景智能体底座 v2.0",
    version="2.0.0"
)

# 必须在这里，第一时间注册 CORS！
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # 确保包含前端地址
    allow_credentials=True,
    allow_methods=["*"], # 这里的 "*" 就是用来放行 OPTIONS 和 POST 的
    allow_headers=["*"],
)

# 2. 定义严格的 Pydantic v2 请求体
class ChatRequest(BaseModel):
    message: str = Field(..., description="用户的原始输入")
    session_id: str = Field(default="default_thread", description="用于隔离多轮对话的会话ID")


# 3. 核心对话接口
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    对前端暴露的统一对话接口。
    内部会自动进行意图识别(Router)和智能体调度(Executor)。
    """
    # 第一步：路由无感分发
    target_plugin = await classify_intent(request.message)
    print(f"🚦 [Supervisor Router] 意图识别完成，当前流量已路由至 -> {target_plugin}")

    # 第二步：透传给底层通用执行器
    response = await run_agent(
        user_input=request.message,
        plugin_name=target_plugin,
        session_id=request.session_id
    )

    # 返回结构化的 JSON 数据
    return {
        "status": "success",
        "plugin_used": target_plugin,
        "reply": response
    }