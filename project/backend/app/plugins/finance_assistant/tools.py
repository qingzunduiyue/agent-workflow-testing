# app/plugins/finance_assistant/tools.py

import yfinance as yf
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# 1. 严格的 Pydantic v2 输入校验 (符合项目架构要求)
class StockQueryInput(BaseModel):
    ticker: str = Field(...,
                        description="标准股票代码。美股直接输入（如 AAPL, TSLA），A股需带后缀（如 600519.SS 代表贵州茅台，000858.SZ 代表五粮液）")


class NewsQueryInput(BaseModel):
    ticker: str = Field(..., description="标准股票代码，用于查询相关公司的最新财务资讯")


# 2. 真实行情获取工具 (带工业级异常处理)
@tool(args_schema=StockQueryInput)
def get_stock_price(ticker: str) -> str:
    """当用户询问某只具体股票的最新价格、涨跌幅时，调用此工具获取真实数据。"""
    try:
        stock = yf.Ticker(ticker)
        # 实时获取市场数据 (yfinance 的 info 字段较丰富)
        info = stock.info

        # 容错处理：不同类型资产（股票/ETF）的字段可能略有不同
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        previous_close = info.get("previousClose")
        short_name = info.get("shortName", ticker)

        if not current_price or not previous_close:
            return f"⚠️ 数据源暂时无法获取 {ticker} 的实时行情，请核对股票代码是否规范（如 A股需加 .SS 或 .SZ）。"

        # 计算涨跌幅
        change_pct = ((current_price - previous_close) / previous_close) * 100
        trend = "上涨 📈" if change_pct > 0 else "下跌 📉"

        return (f"【{short_name} ({ticker}) 实时行情】\n"
                f"- 当前价格: {current_price}\n"
                f"- 昨收价格: {previous_close}\n"
                f"- 今日涨跌: {change_pct:.2f}% ({trend})\n"
                f"- 计价货币: {info.get('currency', '未知')}")

    except Exception as e:
        return f"❌ 查询 {ticker} 行情时发生底层 API 错误: {str(e)}"


# 3. 真实公司资讯工具
@tool(args_schema=NewsQueryInput)
def get_financial_news(ticker: str) -> str:
    """当用户询问某家公司的近期基本面、新闻头条或动态时调用此工具。"""
    try:
        stock = yf.Ticker(ticker)
        news_list = stock.news

        if not news_list:
            return f"暂未查到与 {ticker} 相关的最新资讯。"

        # 提取前三条最新新闻
        formatted_news = [f"- {item['title']} (发布于: {item.get('publisher', '未知')})" for item in news_list[:3]]
        return f"【{ticker} 最新资讯】\n" + "\n".join(formatted_news)

    except Exception as e:
        return f"❌ 查询 {ticker} 资讯时发生错误: {str(e)}"


FINANCE_TOOLS = [get_stock_price, get_financial_news]