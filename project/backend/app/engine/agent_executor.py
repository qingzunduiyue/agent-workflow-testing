from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END

from app.engine.llm_client import get_llm
from app.engine.state import WorkflowState
from app.engine.guardrail import guardrail_node

# ==========================================
# 🆕 1. 引入旅行助手最新的“多智能体流转入口”
# ==========================================


# 保留其他单体插件的导入
from app.plugins.novel_writer.prompts import NOVEL_WRITER_PROMPT
from app.plugins.finance_assistant.prompts import FINANCE_ASSISTANT_PROMPT



# 全局记忆点
memory = MemorySaver()


def get_plugin_config(plugin_name: str):
    # ==========================================
    # 🧹 2. 移除 travel_assistant，因为它现在不归这里管了
    # ==========================================
    if plugin_name == "novel_writer":
        from app.data.novel_settings.rag_tool import retrieve_novel_settings
        return NOVEL_WRITER_PROMPT, [retrieve_novel_settings]
    elif plugin_name == "finance_assistant":
        from app.plugins.finance_assistant.tools import FINANCE_TOOLS
        return FINANCE_ASSISTANT_PROMPT, FINANCE_TOOLS
    else:
        return "你是一个有用的通用AI助手。", []


# ==========================================
# 本地节点与条件边 (用于图的闭环)
# ==========================================
def check_safety(state: WorkflowState) -> str:
    if not state.get("is_safe", True):
        return "blocker_node"
    return "executor_node"


async def blocker_node(state: WorkflowState) -> dict:
    return {"final_response": f"⚠️ {state['risk_reason']}"}


async def executor_node(state: WorkflowState) -> dict:
    plugin_name = state["plugin_name"]

    # ==========================================
    # 🌟 3. 核心路由拦截：将旅行任务外包给多智能体流水线
    # ==========================================
    if plugin_name == "travel_assistant":
        # 直接调用封装好的多智能体流转图
        from app.plugins.travel_assistant.graph import run_travel_agent
        final_text = await run_travel_agent(state["user_input"], state["session_id"])
        return {"final_response": final_text}

    # === 以下是其他单体插件（小说、金融）的老路 ===
    from app.core.config import settings
    if settings.DEMO_MODE:
        from app.engine.demo import demo_reply
        return {"final_response": demo_reply(plugin_name, state["user_input"])}
    llm = get_llm()
    sys_prompt, tools = get_plugin_config(plugin_name)
    config = {"configurable": {"thread_id": state["session_id"]}}

    # 兼容最新版 API
    agent = create_react_agent(llm, tools, prompt=sys_prompt, checkpointer=memory)
    inputs = {"messages": [HumanMessage(content=state["user_input"])]}
    response = await agent.ainvoke(inputs, config=config)

    return {"final_response": response["messages"][-1].content}


# ==========================================
# 编译图拓扑 (Graph Compilation)
# ==========================================
builder = StateGraph(WorkflowState)

# 注册节点：直接挂载外部导入的 guardrail_node
builder.add_node("guardrail_node", guardrail_node)
builder.add_node("blocker_node", blocker_node)
builder.add_node("executor_node", executor_node)

# 编排图结构
builder.add_edge(START, "guardrail_node")
builder.add_conditional_edges(
    "guardrail_node",
    check_safety,
    {"blocker_node": "blocker_node", "executor_node": "executor_node"}
)
builder.add_edge("blocker_node", END)
builder.add_edge("executor_node", END)

workflow = builder.compile()


# ==========================================
# 对外唯一 API
# ==========================================
async def run_agent_with_state(user_input: str, plugin_name: str = "default", session_id: str = "default_thread") -> dict:
    initial_state = {
        "user_input": user_input,
        "plugin_name": plugin_name,
        "session_id": session_id,
    }

    result = await workflow.ainvoke(initial_state)
    return result

async def run_agent(user_input: str, plugin_name: str = "default", session_id: str = "default_thread") -> str:
    """Preserve the existing string-returning entry point for direct callers."""
    result = await run_agent_with_state(user_input, plugin_name, session_id)
    return result["final_response"]
