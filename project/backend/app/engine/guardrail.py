from app.engine.state import WorkflowState

async def guardrail_node(state: WorkflowState) -> dict:
    """全局风控前置节点：极速拦截违规或偏离基调的输入"""
    user_input = state["user_input"]
    is_safe = True
    risk_reason = ""

    # 1. 金融合规护栏 (强阻断)
    finance_risk_words = ["内幕交易", "保证暴利", "推荐个股", "带单", "稳赚"]
    if any(word in user_input for word in finance_risk_words):
        is_safe = False
        risk_reason = "触发金融合规护栏：您的请求涉及敏感投资建议，根据 NFA 合规要求已被系统拦截。"

    # 2. 网文内容与风格护栏 (基调锁)
    novel_risk_words = ["极度虐主", "全员黑化", "传统套路", "血腥暴力"]
    if any(word in user_input for word in novel_risk_words):
         is_safe = False
         risk_reason = "触发网文风控：当前情节设定偏离了轻松治愈与远瞳式吐槽流的核心基调，或破坏了非套路化的世界观漏洞设定，请重新调整。"

    return {"is_safe": is_safe, "risk_reason": risk_reason}