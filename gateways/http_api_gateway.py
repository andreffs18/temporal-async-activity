import logging

import httpx
from pydantic import BaseSettings

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class HttpApiSettings(BaseSettings):
    host: str
    timeout: int = 60

    class Config:
        case_sensitive = False
        env_prefix = "HTTP_API_"


class HttpApiClient(httpx.AsyncClient):
    def __init__(self, settings: HttpApiSettings = HttpApiSettings()):
        super(HttpApiClient, self).__init__(base_url=settings.host, timeout=settings.timeout)

    async def post_request(self, payload: dict) -> httpx.Response:
        url = f"{self.base_url}/request"
        logger.info(f"Making http request to {url=} with {payload=}")
        response = await self.post(url=url, json=payload)
        response.raise_for_status()
        return response
