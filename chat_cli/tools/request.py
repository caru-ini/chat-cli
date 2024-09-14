import textwrap

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from ..utils.tool_loader import BaseTool


class RequestsToolSchema(BaseModel):
    url: str = Field(..., title="URL", description="The URL to send the request to.")
    method: str = Field(
        default="GET", title="Method", description="The HTTP method to use."
    )
    headers: dict = Field(
        default={}, title="Headers", description="The headers to send with the request."
    )
    data: dict = Field(
        default={}, title="Data", description="The data to send with the request."
    )
    raw_response: bool = Field(
        default=False,
        title="Raw Response",
        description="If True, return the raw response (status code, headers, text).",
    )


class RequestsTool(BaseTool):
    name = "Requests"
    description = "Send web requests and process the response."
    schema = RequestsToolSchema

    def run(self, **kwargs) -> dict:
        url = kwargs.get("url")
        method = kwargs.get("method", "GET")
        headers = kwargs.get("headers", {})
        data = kwargs.get("data", {})
        raw_response = kwargs.get("raw_response", False)

        if not url:
            return {"error": "No URL provided."}

        try:
            response = requests.request(method, url, headers=headers, data=data)
            response.raise_for_status()
        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}

        if raw_response:
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.text,
            }
        else:
            return self._process_response(response)

    async def arun(self, **kwargs) -> dict:
        return self.run(**kwargs)

    def _process_response(self, response) -> dict:
        content_type = response.headers.get("Content-Type", "").lower()

        if "text/html" in content_type:
            return self._process_html(response.text)
        elif "application/json" in content_type:
            return self._process_json(response.json())
        else:
            return self._process_text(response.text)

    def _process_html(self, html_content: str) -> dict:
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return {"summary": self._summarize_text(text)}

    def _process_json(self, json_content: dict) -> dict:
        return {"summary": f"JSON response: {json_content}"}

    def _process_text(self, text_content: str) -> dict:
        return {"summary": self._summarize_text(text_content)}

    def _summarize_text(self, text: str, max_length: int = 1000) -> str:
        if len(text) <= max_length:
            return text
        return textwrap.shorten(text, width=max_length, placeholder="...")
