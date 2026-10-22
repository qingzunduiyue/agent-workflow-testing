from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.engine.llm_client import get_llm
from app.engine.state import WorkflowState


# 1. 严格定义路由出口枚举
class IntentRoute(BaseModel):
    plugin_name: Literal["travel_assistant", "novel_writer", "finance_assistant", "default"] = Field(
        ...,
        description="根据用户输入判断需要调用的场景插件名称。"
    )


# 2. 核心路由分发逻辑
async def classify_intent(user_input: str) -> str:
    """超轻量级意图分类器，基于通用 Parser 保证 100% 模型兼容性"""
    from app.core.config import settings
    if settings.DEMO_MODE:
        for name, words in [
            ('travel_assistant', ['旅行', '旅游', '行程', '天气', '攻略']),
            ('finance_assistant', ['股票', '金融', '行情', '投资', 'AAPL']),
            ('novel_writer', ['小说', '故事', '设定', '人物'])]:
            if any(word in user_input for word in words):
                return name
        return 'default'
    llm = get_llm()

    # 【核心修改】：放弃 with_structured_output，改用 PydanticOutputParser
    parser = PydanticOutputParser(pydantic_object=IntentRoute)

    system_prompt = """你是一个多场景智能体框架的核心路由调度中枢（Supervisor）。
你的唯一任务是分析用户的输入意图，并将其精准分发给最合适的专业 Agent。

【可用路由节点说明】
- travel_assistant: 处理旅游规划、天气查询、航班景点安排。
- novel_writer: 处理网文小说创作、构思、设定讨论。
- finance_assistant: 处理股票查询、宏观经济资讯、理财风险评估。
- default: 闲聊、通用知识问答，或以上三种都不符合的请求。

请严格按照以下 JSON 格式输出你的分析结果，不要包含任何额外的解释文本：
{format_instructions}
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])

    # 组装 Chain：Prompt -> LLM -> Parser 解析校验
    chain = prompt | llm | parser

    # 传入 input 以及 parser 自动生成的格式指令
    result = await chain.ainvoke({
        "input": user_input,
        "format_instructions": parser.get_format_instructions()
    })

    return result.plugin_name


async def router_node(state: WorkflowState) -> dict:
    """
    Supervisor 路由调度中枢
    """
    last_message = state["messages"][-1].content

    # 调用你现有的 Parser + Prompt 链路
    # 例如: result = await your_existing_chain.ainvoke({"query": last_message})
    # 为了演示，此处直接返回识别结果
    plugin_name = "default"

    return {"plugin_name": plugin_name}