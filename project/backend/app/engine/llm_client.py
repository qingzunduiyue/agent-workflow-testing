from app.core.config import settings

def get_llm():
    if settings.DEMO_MODE:
        raise RuntimeError('演示模式不调用外部模型')
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError('真实模型模式需要配置 DEEPSEEK_API_KEY')
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_API_BASE, model=settings.MODEL_NAME,
        temperature=0.7, timeout=60, max_retries=1)
