from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import openai
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from rich import print as rprint
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from .tool_loader import load_tools, to_openai_format

PKG_PATH = Path(__file__).parent.parent


class ChatSession:
    def __init__(
        self,
        chat_id: Optional[str] = None,
        messages: Optional[List[ChatCompletionMessageParam]] = None,
        model: str = "gpt-4-1106-preview",
    ):
        self.chat_id: str = chat_id or str(uuid4())
        self.model: str = model
        self.messages: List[ChatCompletionMessageParam] = messages or [
            {
                "role": "system",
                "content": f"""You are a chat AI assistant. When you use a tool, carefully read and incorporate the 'Tool results' message in your response.
                Current date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                """,
            }
        ]
        self.tools = load_tools(PKG_PATH / "tools")
        self.enable_tool: bool = True
        self.tool_fail_count: int = 0
        print(self.tool_names())

    @classmethod
    def from_message(cls, message: ChatCompletionMessageParam) -> "ChatSession":
        chat_session = cls(message.get("chat_id"))
        chat_session.add_message(message)
        return chat_session

    def add_message(self, message: ChatCompletionMessageParam) -> None:
        self.messages.append(message)

    def get_messages(self) -> List[ChatCompletionMessageParam]:
        return self.messages

    def get_chat_id(self) -> str:
        return self.chat_id

    def send_message(
        self, message: ChatCompletionMessageParam, console: Optional[Console] = None
    ) -> None:
        _console = console or Console()
        content = Markdown("")
        ui_buffer: List[str] = []

        with Live(
            Panel(content, expand=False), refresh_per_second=20, console=_console
        ) as live:
            self.messages.append(message)

            while True:
                tool_results: Dict[str, Any] = {}
                buffer: List[str] = []
                finish_reason: Optional[str] = None
                tc_arg_buffer: List[str] = []
                tc_name: Optional[str] = None

                def update_ui() -> None:
                    live.update(Panel(Markdown("".join(ui_buffer)), expand=False))

                params = {
                    "model": self.model,
                    "messages": self.messages,
                    "stream": True,
                }

                if self.tools and self.tool_fail_count <= 1:
                    params["tools"] = [to_openai_format(tool) for tool in self.tools]

                stream: openai.Stream[ChatCompletionChunk] = (
                    openai.chat.completions.create(**params)
                )

                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            function = tc.function
                            if not function:
                                continue

                            if not function.name and not tc_name:
                                continue
                            if not tc_name:
                                tc_name = function.name
                            tc_arg_buffer.append(function.arguments or "")

                            try:
                                args = json.loads("".join(tc_arg_buffer))
                            except json.JSONDecodeError:
                                continue

                            if not tc_name:
                                continue

                            ui_buffer.append(
                                f"Running tool: {tc_name} \n\n {args} \n\n"
                            )
                            update_ui()

                            tool_result = self.execute_tool(tc_name, args)
                            if tool_result:
                                tool_results[tc_name.lower()] = tool_result
                                update_ui()

                    if delta.content:
                        buffer.append(delta.content)
                        ui_buffer.append(delta.content)
                        update_ui()

                    if chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason
                        break

                self.process_message_buffer(buffer)
                self.process_tool_results(tool_results)

                if finish_reason != "tool_calls":
                    if finish_reason != "stop":
                        rprint(
                            f"[red]Chat stopped unexpectedly. Reason: {finish_reason}[/red]"
                        )
                    break

            update_ui()

    def execute_tool(
        self, tool_name: str, args: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        tool = next((tool for tool in self.tools if tool.name == tool_name), None)
        if not tool:
            self.tool_fail_count += 1
            return None

        result = tool.run(**args)
        if result.get("error"):
            self.tool_fail_count += 1
        else:
            self.tool_fail_count = 0
        return result

    def tool_names(self) -> List[str]:
        return [tool.name for tool in self.tools]

    def process_message_buffer(self, buffer: List[str]) -> None:
        if buffer:
            assistant_message: ChatCompletionMessageParam = {
                "role": "assistant",
                "content": "".join(buffer),
            }
            self.messages.append(assistant_message)

    def process_tool_results(self, tool_results: Dict[str, Any]) -> None:
        if tool_results:
            tool_result_message: ChatCompletionMessageParam = {
                "role": "system",
                "content": f"Tool results:\n{json.dumps(tool_results, indent=2)}\n\nPlease incorporate this information in your response.",
            }
            self.messages.append(tool_result_message)

    def __str__(self) -> str:
        return f"ChatSession(chat_id={self.chat_id}, messages={self.messages})"

    def __repr__(self) -> str:
        return str(self)
