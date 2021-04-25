from abc import ABC
from typing import Any, Dict, Optional
from urllib import parse as urlparse

import requests


class HTTPAPI(ABC):
    def __init__(self, url: str, cache: Optional[Dict[str, Any]] = None) -> None:
        self.url = url
        self.headers = {}
        self.cache = cache or {}

    def uri(self, endpoint: str) -> str:
        return urlparse.urljoin(self.url, endpoint)

    def get(self, endpoint: str, use_cache: bool = False, **kwargs: Any) -> Any:
        cache_key = f"get:{endpoint}?{urlparse.urlencode(kwargs)}"
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]

        res = requests.get(url=self.uri(endpoint), headers=self.headers, params=kwargs)
        res.raise_for_status()
        res_json = res.json()
        self.cache[cache_key] = res_json
        return res_json
