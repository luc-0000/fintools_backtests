import json
import os
from datetime import datetime
from typing import List, Dict, Any
import requests
from local_agents.tauric_mcp.agents.utils.utils import NewsItem
import dotenv
dotenv.load_dotenv()


def baidu_search(query: str, num_results: int = 10, recent: str = "week")->List[NewsItem]:
    """
    Baidu recent: week, month, semiyear, year

    Returns results formatted according to SearchItem model.
    """

    BAIDU_API_KEY = os.getenv("BAIDU_API_KEY")

    url = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"

    payload = json.dumps({
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "search_source": "baidu_search_v2",
        "search_recency_filter": recent,
        "resource_type_filter": [{"type": "web", "top_k": num_results}]
    }, ensure_ascii=False)

    headers = {
        'Authorization': f"Bearer {BAIDU_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))

    if response.status_code != 200:
        return []
    raw_results = response.json().get('references')

    results = []
    for i, item in enumerate(raw_results):
        if isinstance(item, str):
            # If it's just a URL
            results.append(
                {"title": f"BaiduAPI Result { i +1}", "url": item, "description": ""}
            )
        else:
            results.append(
                NewsItem(
                    title=item.get('title'),
                    url=item.get('url'),
                    content=item.get('content'),
                    publish_time=datetime.strptime(item.get('date'),"%Y-%m-%d %H:%M:%S"),
                    source=item.get('website'),
                    urgency='low',
                    relevance_score=None
                )
            )

    return results

def baidu_ai_search(query: str, num_results: int = 10, recent: str = "week")->List[NewsItem]:
    """
    Baidu recent: week, month, semiyear, year

    Returns results formatted according to SearchItem model.
    """

    BAIDU_API_KEY = os.getenv("BAIDU_API_KEY")

    url = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"

    payload = json.dumps({
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "model": "deepseek-r1",
        "search_source": "baidu_search_v2",
        "search_recency_filter": recent,
        "resource_type_filter": [{"type": "web", "top_k": num_results}],
        "instruction": "深度搜索该股票最近信息",
        "enable_deep_search": False
    }, ensure_ascii=False)

    headers = {
        'Authorization': f"Bearer {BAIDU_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))

    if response.status_code != 200:
        return []
    raw_results = response.json().get('references')

    results = []
    for i, item in enumerate(raw_results):
        if isinstance(item, str):
            # If it's just a URL
            results.append(
                {"title": f"BaiduAPI Result { i +1}", "url": item, "description": ""}
            )
        else:
            results.append(
                NewsItem(
                    title=item.get('title'),
                    url=item.get('url'),
                    content=item.get('content'),
                    publish_time=datetime.strptime(item.get('date'),"%Y-%m-%d %H:%M:%S"),
                    source=item.get('website'),
                    urgency='low',
                    relevance_score=None
                )
            )

    return results


def bocha_search(
    query: str,
    freshness: str = "oneWeek",
    summary: bool = True,
    page: int = 1,
    number_of_result_pages: int = 10,
) ->List[NewsItem]:
    r"""Query the Bocha AI search API and return search results.

    Args:
        query (str): The search query.
        freshness (str): Time frame filter for search results. Default
            is "noLimit". Options include:
            - 'noLimit': no limit (default).
            - 'oneDay': past day.
            - 'oneWeek': past week.
            - 'oneMonth': past month.
            - 'oneYear': past year.
        summary (bool): Whether to include text summaries in results.
            Default is False.
        page (int): Page number of results. Default is 1.
        number_of_result_pages (int): The number of result pages to
            retrieve. Adjust this based on your task - use fewer results
            for focused searches and more for comprehensive searches.
            (default: :obj:`10`)

    Returns:
        Dict[str, Any]: A dictionary containing search results, including
            web pages, images, and videos if available. The structure
            follows the Bocha AI search API response format.
    """
    BOCHA_API_KEY = os.getenv("BOCHA_API_KEY")

    url = "https://api.bochaai.com/v1/web-search"
    headers = {
        "Authorization": f"Bearer {BOCHA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = json.dumps(
        {
            "query": query,
            "freshness": freshness,
            "summary": summary,
            "count": number_of_result_pages,
            "page": page,
        },
        ensure_ascii=False,
    )
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code != 200:
            print(f"{response.status_code}: {response.text}")
            return []

        raw_results = response.json().get("data").get('webPages').get('value')
        results = []
        for i, item in enumerate(raw_results):
            if isinstance(item, str):
                # If it's just a URL
                results.append(
                    {"title": f"Bocha API Result {i + 1}", "url": item, "description": ""}
                )
            else:
                results.append(
                    NewsItem(
                        title=item.get('name'),
                        url=item.get('url'),
                        content=item.get('summary'),
                        publish_time=datetime.strptime(item.get('datePublished').split('+')[0], "%Y-%m-%dT%H:%M:%S"),
                        source=item.get('siteName'),
                        urgency='low',
                        relevance_score=None
                    )
                )
        return results
    except requests.exceptions.RequestException as e:
        print(e)
        return []

def bocha_ai_search(
    query: str,
    freshness: str = "oneWeek",
    include: str = '',
    number_of_result_pages: int = 10,
    answer: bool = False,
    stream:bool = False
) ->List[NewsItem]:
    r"""Query the Bocha AI search API and return search results.
    Args:
        query (str): The search query.
        freshness (str): Time frame filter for search results. Default
            is "noLimit". Options include:
            - 'noLimit': no limit (default).
            - 'oneDay': past day.
            - 'oneWeek': past week.
            - 'oneMonth': past month.
            - 'oneYear': past year.
    """
    BOCHA_API_KEY = os.getenv("BOCHA_API_KEY")

    url = "https://api.bochaai.com/v1/ai-search"
    headers = {
        "Authorization": f"Bearer {BOCHA_API_KEY}",
        "Content-Type": "application/json",
        "Connection": "keep-alive ",
        "Accept": "*/*"
    }

    payload = json.dumps(
        {
            "query": query,
            "freshness": freshness,
            "include": include,
            "count": number_of_result_pages,
            "answer": answer,
            "stream":stream
        },
        ensure_ascii=False,
    )
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code != 200:
            print(f"{response.status_code}: {response.text}")
            return []

        raw_results = response.json().get("messages")[0].get('content')
        raw_results = json.loads(raw_results).get('value')
        results = []
        for i, item in enumerate(raw_results):
            if isinstance(item, str):
                # If it's just a URL
                results.append(
                    {"title": f"Bocha API Result {i + 1}", "url": item, "description": ""}
                )
            else:
                results.append(
                    NewsItem(
                        title=item.get('name'),
                        url=item.get('url'),
                        content=item.get('summary'),
                        publish_time=datetime.strptime(item.get('datePublished').split('+')[0], "%Y-%m-%dT%H:%M:%S"),
                        source=item.get('siteName'),
                        urgency='low',
                        relevance_score=None
                    )
                )
        return results
    except requests.exceptions.RequestException as e:
        print(e)
        return []