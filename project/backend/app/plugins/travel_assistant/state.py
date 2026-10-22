from typing import TypedDict, Annotated, List
import operator
from langchain_core.messages import BaseMessage


class TravelState(TypedDict):
    # ==========================================
    # 基础上下文 (继承自主路由的输入)
    # ==========================================
    user_input: str
    session_id: str

    # LangGraph 标准消息流，使用 operator.add 确保多 Agent 追加消息而不是相互覆盖
    messages: Annotated[List[BaseMessage], operator.add]

    # ==========================================
    # 多智能体协同专属“半成品”槽位
    # ==========================================
    # 1. 探路者 (Researcher) 专属输出槽
    # 存放扒下来的纯客观数据：航班号、酒店价格、景点营业时间等干货。
    research_data: str

    # 2. 主笔人 (Writer) 专属输出槽
    # 存放基于干货生成的初稿（例如带有大量 Emoji 的小红书种草文案风格）。
    draft_content: str

    # 3. 质检员 (Reviewer) 专属输出槽
    # 存放逻辑查杀结果，例如“第一天晚上在乌鲁木齐，第二天早上不可能秒到喀纳斯，请修改行程”。
    review_feedback: str

    # ==========================================
    # 路由控制信号 (Control Flags)
    # ==========================================
    # 决定图节点走向的关键布尔值：质检是否通过？
    is_approved: bool

    # 熔断机制：记录被打回重写的次数。防止质检员和主笔人陷入“无限互喷”的死循环。
    revision_count: int