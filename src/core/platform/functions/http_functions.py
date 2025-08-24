from dataclasses import dataclass
from typing import Optional, List


@dataclass
class HTTPFunctionParams:
    """
    Parameters for executing a function.
    """

    name: List[str]
    url: List[str]
    method: str
    headers: Optional[dict] = None
    body: Optional[dict] = None


class HTTPFunction:
    """
    Class to execute HTTP functions.
    """

    def __init__(self, params: HTTPFunctionParams):
        self.params = params

    async def execute(self):
        import aiohttp

        headers = self.params.headers or {}
        body = self.params.body or {}

        # Handle both single URL and list of URLs
        url = (
            self.params.url[0] if isinstance(self.params.url, list) else self.params.url
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=self.params.method,
                    url=url,
                    headers=headers,
                    json=body if body else None,
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            raise Exception(f"HTTP request failed: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error in HTTP request: {e}")
