from dataclasses import dataclass
from typing import Optional


@dataclass
class HTTPFunctionParams:
    """Parameters for executing an HTTP function."""

    name: str
    url: str
    method: str
    headers: Optional[dict] = None
    body: Optional[dict] = None
    timeout: float = 30.0


class HTTPFunction:
    """Executes a single HTTP request."""

    def __init__(self, params: HTTPFunctionParams):
        self.params = params

    async def execute(self):
        import aiohttp

        headers = self.params.headers or {}
        body = self.params.body or {}
        timeout = aiohttp.ClientTimeout(total=self.params.timeout)

        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {}
                if body and self.params.method.upper() not in ("GET", "DELETE"):
                    kwargs["json"] = body

                async with session.request(
                    method=self.params.method,
                    url=self.params.url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs,
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientResponseError as e:
            raise Exception(f"HTTP {e.status} error for {self.params.url}: {e.message}")
        except aiohttp.ClientError as e:
            raise Exception(f"HTTP request failed for {self.params.url}: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error in HTTP request: {e}")
