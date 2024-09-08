from __future__ import annotations

import importlib
import inspect
from abc import ABC, abstractmethod
from logging import getLogger
from pathlib import Path
from typing import Any, Type

from pydantic import BaseModel

# model meta class

logger = getLogger(__name__)


class BaseTool(ABC):
    name: str
    description: str
    schema: Type[BaseModel]

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    async def arun(self, *args, **kwargs) -> Any:
        pass


def load_tools(path: Path, tools: list[str] = []) -> list[BaseTool]:
    """
    Load the tools from the specified path and return them as a dictionary.

    Args:
    path (Path): The path to the directory which contains the tools.
    tools (list[str]): A list of tool names to load.

    Returns:
    list[BaseTool]: A list of loaded tools.
    """
    load_all = not tools
    loaded_tools: list[BaseTool] = []
    error_tools = []

    for file in path.rglob("*.py"):
        try:
            # exclude __init__ and __pycache__ files
            if file.stem == "__init__" or file.parent.stem == "__pycache__":
                continue

            # Convert the file path to a module name
            module_name = f".{file.stem}"

            module = importlib.import_module(module_name, package="chat_cli.tools")

            def is_valid_tool(obj: object) -> bool:
                return (
                    inspect.isclass(obj)
                    and obj != BaseTool
                    and hasattr(obj, "name")
                    and hasattr(obj, "description")
                    and hasattr(obj, "schema")
                    and callable(getattr(obj, "run", None))
                    and callable(getattr(obj, "arun", None))
                )

            if load_all:
                tools = [
                    name
                    for name, obj in inspect.getmembers(module, inspect.isclass)
                    if is_valid_tool(obj)
                ]

            # print(tools)

            # Iterate over the list of tool names to load
            for tool_name in tools:
                # Check if the module has a class that ends with 'Tool'
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if name == tool_name and is_valid_tool(obj):
                        print(f"Loaded tool: {tool_name}")
                        loaded_tools.append(obj())
        except Exception as e:
            error_tools.append((file.name, str(e)))

    if error_tools:
        logger.error("Error loading tools:")
        logger.error(error_tools)

    return loaded_tools


def to_openai_format(tool) -> dict[str, Any]:
    """
    Convert Tool class to OpenAI tool format.

    Args:
    tool (Any): The tool to convert.

    Returns:
    dict[str, Any]: A dictionary of tool names and their classes.
    """
    output = {}
    # get schema from tool
    schema: BaseModel = tool.schema

    # generate json schema
    output["name"] = tool.name
    output["description"] = tool.description
    output["parameters"] = schema.model_json_schema()
    return {
        "type": "function",
        "function": output,
    }
