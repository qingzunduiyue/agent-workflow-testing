from app.core.config import settings

def get_travel_tools():
    if not settings.tavily_api_key:
        raise RuntimeError('旅行实时搜索需要配置 TAVILY_API_KEY')
    from langchain_tavily import TavilySearch
    return [TavilySearch(tavily_api_key=settings.tavily_api_key, max_results=3,
        description='查询实时旅行信息；引用搜索结果，不能编造实时数据。')]
