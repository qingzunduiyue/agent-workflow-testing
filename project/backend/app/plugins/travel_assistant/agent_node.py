# app/plugins/travel_assistant/agent_nodes.py
import operator
from typing import Annotated, TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

# 引入全局 LLM 和你刚刚定义好的工具
from app.engine.llm_client import get_llm
from app.core.config import settings


# ==========================================
# 1. 状态契约 (TravelState)
# ==========================================
class TravelState(TypedDict):
    user_input: str
    session_id: str
    messages: Annotated[list[BaseMessage], operator.add]

    research_data: str  # 探路者收集的客观干货
    draft_content: str  # 主笔人润色后的初稿
    review_feedback: str  # 质检员的查杀与修改意见

    is_approved: bool  # 路由走向信号：是否通过审核
    revision_count: int  # 熔断机制：记录重写次数


# ==========================================
# 2. 角色提示词 (System Prompts)
# ==========================================
RESEARCHER_PROMPT = """你是一个冷酷、高效的旅行规划调查员。
你的唯一职责是使用 TavilySearch 工具检索全网最新信息，为下游的文案团队提供绝对真实、客观的“干货素材”。
包含：近期天气、核心景点营业状态、真实的交通距离、避坑指南。
绝不修饰辞藻，直接输出高密度的干货数据列表。"""

WRITER_PROMPT = """你是一个深谙社交媒体爆款逻辑的顶级旅行博主。
你的任务是将调查员提供的干货，转化为极具种草感和煽动性的攻略文案。
【排版与语气铁律】
1. 必须生成极具网感、抓人眼球的吸睛标题。
2. 必须在段落和关键点中高频使用 Emoji 表情符号（如 ✈️🏨🍜📸 等）。
3. 语气要像闺蜜安利一样亲切、热情，提供满满的情绪价值。
4. 严格输出为 Markdown 格式，不要多余的寒暄和废话。"""


# ==========================================
# 3. 质检员的 Pydantic 输出契约
# ==========================================
class ReviewResult(BaseModel):
    is_approved: bool = Field(description="行程是否符合物理现实逻辑且没有严重遗漏？通过为 True，打回为 False")
    feedback: str = Field(
        description="如果打回，请详细说明修改意见（如：两地距离太远一天跑不完）。如果通过，回复 '一切完美'。")


# ==========================================
# 4. 智能体节点逻辑 (Agents)
# ==========================================

async def researcher_node(state: TravelState) -> dict:
    if settings.DEMO_MODE:
        return {"research_data": "固定示例：两天步行游览；实际天气、交通和营业时间需另行查询。"}
    from app.plugins.travel_assistant.tools import get_travel_tools
    TRAVEL_TOOLS = get_travel_tools()
    pass  # Debug-only console output omitted.
    llm = get_llm()
    # 挂载真实的 Tavily 搜索工具
    agent = create_react_agent(llm, TRAVEL_TOOLS, prompt=RESEARCHER_PROMPT)

    query = f"用户需求：{state['user_input']}"
    if state.get("review_feedback") and not state.get("is_approved"):
        pass  # Debug-only console output omitted.
        query += f"\n\n🚨 质检打回意见，请补充检索：\n{state['review_feedback']}"

    response = await agent.ainvoke({"messages": [HumanMessage(content=query)]})
    return {"research_data": response["messages"][-1].content}


async def writer_node(state: TravelState) -> dict:
    if settings.DEMO_MODE:
        return {"draft_content": "**演示模式：未联网、未调用模型，以下为固定行程示例。**\n\n第一天：市区步行与博物馆。第二天：公园与地方美食。\n\n调查节点提供：" + state["research_data"]}
    pass  # Debug-only console output omitted.
    llm = get_llm()
    # 挂载空工具数组，纯靠 Prompt 转换文风
    agent = create_react_agent(llm, [], prompt=WRITER_PROMPT)

    context = f"用户原始需求：{state['user_input']}\n\n客观干货数据：\n{state['research_data']}"
    if state.get("review_feedback") and not state.get("is_approved"):
        pass  # Debug-only console output omitted.
        context += f"\n\n🚨 质检打回，请根据以下意见修改文案：\n{state['review_feedback']}"

    response = await agent.ainvoke({"messages": [HumanMessage(content=context)]})
    return {"draft_content": response["messages"][-1].content}


async def reviewer_node(state: TravelState) -> dict:
    if settings.DEMO_MODE:
        return {"is_approved": True, "review_feedback": "演示流程完成，不代表真实行程审核。", "revision_count": state.get("revision_count", 0) + 1}
    pass  # Debug-only console output omitted.
    llm = get_llm()

    # 回归稳健架构：使用 PydanticOutputParser 兼容所有模型
    parser = PydanticOutputParser(pydantic_object=ReviewResult)

    prompt_template = """你是一个严苛的旅行质检员。请审查以下旅行攻略初稿。
    重点查杀：1. 交通时间/距离是否具有现实可行性？ 2. 是否忽略了天气风险或闭馆风险？

    【初稿内容】：
    {draft_content}

    【输出格式绝对指令】：
    必须严格输出纯 JSON 数据，不要包含任何 Markdown 标记 (如 ```json) 或其他解释性文字。
    {format_instructions}
    """

    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["draft_content"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    # 将 Prompt、LLM 和解析器串联
    chain = prompt | llm | parser

    try:
        # 执行调用
        result: ReviewResult = await chain.ainvoke({"draft_content": state['draft_content']})
    except Exception as e:
        pass  # Debug-only console output omitted.
        # 兜底机制：如果小模型没有按格式输出，为了不卡死整个图，强制放行
        result = ReviewResult(is_approved=True, feedback="格式解析失败，系统默认放行。")

    # 增加重试计数器，防止死循环 (最多允许主笔人修改 2 次)
    current_count = state.get("revision_count", 0) + 1
    if not result.is_approved and current_count >= 2:
        pass  # Debug-only console output omitted.
        result.is_approved = True

    if result.is_approved:
        pass  # Debug-only console output omitted.
    else:
        pass  # Debug-only console output omitted.

    return {
        "is_approved": result.is_approved,
        "review_feedback": result.feedback,
        "revision_count": current_count
    }