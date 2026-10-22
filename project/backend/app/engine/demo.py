from pathlib import Path

def demo_reply(plugin_name: str, user_input: str) -> str:
    heading = '**演示模式：以下为固定示例输出，未调用模型或实时数据。**\n\n'
    if plugin_name == 'novel_writer':
        source = Path(__file__).resolve().parents[1] / 'data' / 'novel_settings' / 'demo_setting.md'
        return heading + '根据公开示例文件 demo_setting.md：\n\n' + source.read_text(encoding='utf-8')
    if plugin_name == 'finance_assistant':
        return heading + '金融助手已选中。真实行情查询需要关闭演示模式并连接数据源；此处不提供虚构报价。'
    return heading + '你好！可以输入“安排两天旅行”“写一个校园故事”或“查询 AAPL 股票行情”，体验场景分发。'
