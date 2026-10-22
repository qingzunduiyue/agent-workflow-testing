from typing import TypedDict

class WorkflowState(TypedDict):
    user_input: str
    plugin_name: str
    session_id: str
    is_safe: bool
    risk_reason: str
    final_response: str