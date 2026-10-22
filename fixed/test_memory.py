import requests
import time

BASE_URL = "http://127.0.0.1:8000/api/chat"


def send_chat_request(message: str, plugin_name: str, session_id: str):
    print(f"\n[User - {session_id}]: {message}")
    payload = {
        "message": message,
        "plugin_name": plugin_name,
        "session_id": session_id
    }

    start_time = time.time()
    try:
        response = requests.post(BASE_URL, json=payload)
        response.raise_for_status()
        reply = response.json().get("reply", response.text)  # 根据你的实际 response 结构调整
        print(f"[Agent]: {reply}")
        print(f"(耗时: {time.time() - start_time:.2f}秒)")
    except Exception as e:
        print(f"[Error]: 请求失败 - {e}")


def run_tests():
    print("=== 开始运行 Multi-Scenario Agent 记忆力测试 ===")

    # ---------------------------------------------------------
    # 测试用例 1: 联网插件 (Travel Assistant) - 验证记忆 + 工具调用
    # ---------------------------------------------------------
    print("\n>>> 场景 A: 旅游规划 (带搜索工具)")
    travel_session = "travel_user_99"

    # 第一轮：抛出意图，触发搜索
    send_chat_request(
        "帮我查一下这周末去大阪的机票趋势和天气。",
        "travel_assistant",
        travel_session
    )

    # 第二轮：省略主语和时间，直接基于上下文追问
    send_chat_request(
        "按照你查到的天气，帮我简单排个两天的行程。记得第一天留出半天时间去逛逛卖漫画周边的地方。",
        "travel_assistant",
        travel_session
    )

    # ---------------------------------------------------------
    # 测试用例 2: 纯文本插件 (Novel Writer) - 验证纯 LLM 状态下的记忆
    # ---------------------------------------------------------
    print("\n>>> 场景 B: 网文辅助创作 (无工具纯文本)")
    novel_session = "author_001"

    # 第一轮：设定极其详细的背景设定
    send_chat_request(
        "这是合成的小说测试输入：主角在校园中发现一件异常事件。",
        "novel_writer",
        novel_session
    )

    # 第二轮：要求基于上一轮的设定进行特定风格的输出
    send_chat_request(
        "请依据上一轮的合成背景，描述主角对异常事件的反应。",
        "novel_writer",
        novel_session
    )


if __name__ == "__main__":
    run_tests()