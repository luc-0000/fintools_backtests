import os
from typing import List, Any, Dict
import requests
from local_agents.fingenius.src.tool.search.base import SearchItem, WebSearchEngine

class BoChaSearchEngine(WebSearchEngine):
    def perform_search(
        self, query: str, num_results: int = 10, freshness: str = "oneWeek", summary: bool = True, page: int = 1, *args, **kwargs
    ) -> List[SearchItem]:
        """
        Bocha freshness: noLimit, oneDay, oneWeek, oneMonth

        Returns results formatted according to SearchItem model.
        """
        import json

        BOCHA_API_KEY = os.getenv("BOCHA_API_KEY")
        # BOCHA_API_KEY = getattr(config.search_config, "api_key")

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
                "count": num_results,
                "page": page,
            },
            ensure_ascii=False,
        )
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code != 200:
            return []
        raw_results = response.json().get('data').get('webPages').get('value')
        # raw_results = search(query, num_results=num_results, advanced=True)

        results = []
        for i, item in enumerate(raw_results):
            if isinstance(item, str):
                # If it's just a URL
                results.append(
                    {"title": f"Bocha Result {i+1}", "url": item, "description": ""}
                )
            else:
                item_title = item.get('name')
                item_url = item.get('url')
                item_description = item.get('summary')
                results.append(
                    SearchItem(
                        title=item_title, url=item_url, description=item_description
                    )
                )

        return results
