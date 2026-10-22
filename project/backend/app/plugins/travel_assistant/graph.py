# app/plugins/travel_assistant/graph.py
from langgraph.graph import StateGraph, START, END

# 引入我们刚才定义好的状态契约和三个智能体节点
from app.plugins.travel_assistant.agent_node import (
    TravelState,
    researcher_node,
    writer_node,
    reviewer_node
)


# ==========================================
# 1. 定义条件流转逻辑 (Conditional Edge)
# ==========================================
def check_approval(state: TravelState) -> str:
    """
    检查质检员的审核结果。
    如果通过，走向终点；如果不通过，打回给探路者重新收集信息并重写。
    """
    if state.get("is_approved", False):
        pass  # Debug-only console output omitted.
        return "approved"
    else:
        pass  # Debug-only console output omitted.
        return "rejected"


# ==========================================
# 2. 编译多智能体状态机 (Graph Compilation)
# ==========================================
# 初始化图，并绑定专属的 TravelState
builder = StateGraph(TravelState)

# 注册车间工位 (Nodes)
builder.add_node("researcher", researcher_node)
builder.add_node("writer", writer_node)
builder.add_node("reviewer", reviewer_node)

# 编排流水线 (Edges)
# 1. 入口 -> 探路者
builder.add_edge(START, "researcher")

# 2. 探路者 -> 主笔人
builder.add_edge("researcher", "writer")

# 3. 主笔人 -> 质检员
builder.add_edge("writer", "reviewer")

# 4. 质检员 -> 条件分支 (核心循环点)
builder.add_conditional_edges(
    "reviewer",
    check_approval,
    {
        "approved": END,  # 审核通过，结束
        "rejected": "researcher"  # 审核失败，带着 feedback 重新回到探路者去查资料
    }
)

# 编译成可执行的 workflow
travel_workflow = builder.compile()


# ==========================================
# 3. 适配底座的无缝对接包 (Wrapper)
# ==========================================
async def run_travel_agent(user_input: str, session_id: str) -> str:
    """
    暴露给外层主路由 (app/engine/agent_executor.py) 的统一调用接口。
    隐藏内部复杂的多智能体流转细节。
    """
    # 初始化状态
    initial_state = {
        "user_input": user_input,
        "session_id": session_id,
        "messages": [],
        "research_data": "",
        "draft_content": "",
        "review_feedback": "",
        "is_approved": False,
        "revision_count": 0
    }

    # 启动多智能体图的流转
    result = await travel_workflow.ainvoke(initial_state)

    # 将主笔人最终定稿的文案返回给主路由
    return result["draft_content"]