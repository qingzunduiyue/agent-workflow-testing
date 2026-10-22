# app/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.engine.router import classify_intent
from app.engine.agent_executor import run_agent_with_state
from fastapi.middleware.cors import CORSMiddleware

# 1. 初始化 FastAPI 实例 (Uvicorn 依赖这个 app)
app = FastAPI(
    title="Multi-Scenario Agent Framework",
    description="多场景 Agent 学习项目：演示模式与真实模型模式",
    version="2.0.0"
)

# 必须在这里，第一时间注册 CORS！
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # 确保包含前端地址
    allow_credentials=True,
    allow_methods=["*"], # 这里的 "*" 就是用来放行 OPTIONS 和 POST 的
    allow_headers=["*"],
)

# 2. 定义严格的 Pydantic v2 请求体
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=20000, description="用户的原始输入")
    session_id: str = Field(default="default_thread", description="用于隔离多轮对话的会话ID")


# 3. 核心对话接口
async def chat_endpoint_impl(request: ChatRequest):
    """
    对前端暴露的统一对话接口。
    内部会自动进行意图识别(Router)和智能体调度(Executor)。
    """
    # 第一步：路由无感分发
    target_plugin = await classify_intent(request.message)
    pass  # Debug-only console output omitted.

    # 第二步：透传给底层通用执行器
    result = await run_agent_with_state(
        user_input=request.message,
        plugin_name=target_plugin,
        session_id=request.session_id
    )

    # 返回结构化的 JSON 数据
    return {
        "status": "success",
        "plugin_used": target_plugin,
        "reply": result["final_response"],
        "is_safe": result.get("is_safe", True),
        "risk_reason": result.get("risk_reason") or None
    }

@app.get('/health')
async def health():
    from app.core.config import settings
    return {'status': 'ok', 'mode': 'demo' if settings.DEMO_MODE else 'live'}

@app.post('/api/chat')
async def chat_endpoint(request: ChatRequest):
    try:
        result = await chat_endpoint_impl(request)
    except (RuntimeError, ImportError) as error:
        raise HTTPException(status_code=503, detail='运行配置或可选依赖未就绪，请检查项目说明与后端日志。') from error
    from app.core.config import settings
    result['mode'] = 'demo' if settings.DEMO_MODE else 'live'
    return result
