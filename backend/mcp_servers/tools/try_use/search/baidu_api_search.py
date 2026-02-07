import json
import os
from typing import List
import requests
from local_agents.fingenius.src.tool.search.base import SearchItem, WebSearchEngine

class BaiduAPISearchEngine(WebSearchEngine):
    def perform_search(
        self, query: str, num_results: int = 10, recent: str = "month", *args, **kwargs
    ) -> List[SearchItem]:
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
                    {"title": f"BaiduAPI Result {i+1}", "url": item, "description": ""}
                )
            else:
                item_title = item.get('title')
                item_url = item.get('url')
                item_description = item.get('content')
                results.append(
                    SearchItem(
                        title=item_title, url=item_url, description=item_description
                    )
                )

        return results
