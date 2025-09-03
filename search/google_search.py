import logging
from tavily import TavilyClient, AsyncTavilyClient
from app.config.settings import settings

logger = logging.getLogger(__name__)
url = f'https://api.valueserp.com/search'


def search_web(query: str):
    """
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for up-to-date information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            },
        }
    }
    """
    tavily = TavilyClient(api_key=settings.tavily_token)
    result = tavily.search(query=query, max_results=5, include_raw_content=False, timeout=120)
    print(result)
    ret = []
    if not result:
        logger.error("search_web return none")
        return ret

    for ele in dict(result).get('results', []):
        raw_content = ele.get('content', "")
        title = ele.get("title", "")
        url = ele.get("url", "")
        ret.append(
            {
                "url": url,
                "title": title,
                "content": raw_content
            }
        )
    logger.info(f"search_web ret = {len(ret)}")
    return ret

