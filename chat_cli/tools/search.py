from duckduckgo_search import DDGS, AsyncDDGS
from pydantic import BaseModel, Field

from ..utils.tool_loader import BaseTool


class SearchToolSchema(BaseModel):
    query: str = Field(..., title="Query", description="The search query.")


class SearchTool(BaseTool):
    name = "Search"
    description = "Search the web for information."
    schema = SearchToolSchema

    def run(self, **kwargs) -> dict:
        query = kwargs.get("query")
        if not query:
            return {"error": "No query provided."}

        with DDGS() as ddgs:
            results = ddgs.text(query)
            return results[0]

    async def arun(self, **kwargs) -> dict:
        query = kwargs.get("query")
        if not query:
            return {"error": "No query provided."}

        async with AsyncDDGS() as ddgs:
            results = ddgs.text(query)
            return results[0]
