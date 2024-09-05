from uuid import uuid4
import openai
from pathlib import Path
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich import print as rprint
import json
from datetime import datetime

from .utils.tool_loader import load_tools, to_openai_format

PKG_PATH = Path(__file__).parent


class ChatSession:
    def __init__(self, chat_id=None, messages=None, model=None):
        self.chat_id = chat_id or str(uuid4())
        self.model = model or "gpt-4o-mini"
        self.messages = messages or [
            {
                "role": "system",
                "content": f"""You are a chat AI assistant. When you use a tool, carefully read and incorporate the 'Tool results' message in your response.
                Current date:{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                """,
            }
        ]
        self.tools = load_tools(PKG_PATH / "tools")
        self.enable_tool = True

    @classmethod
    def from_message(cls, message) -> "ChatSession":
        chat_id = message.chat_id
        chat_session = cls(chat_id)
        chat_session.add_message(message)
        return chat_session

    def add_message(self, message):
        self.messages.append(message)

    def get_messages(self):
        return self.messages

    def get_chat_id(self):
        return self.chat_id

    def send_message(
        self, message: ChatCompletionMessageParam, console: Console = None
    ):
        _console = console or Console()
        content = Markdown("")
        ui_buffer = []

        with Live(
            Panel(content, expand=False),
            refresh_per_second=20,
            console=console,
        ) as live:
            tool_fail_count = 0
            self.messages.append(message)

            while True:
                tool_results = {}
                buffer = []
                finish_reason = None
                tc_arg_buffer = []
                tc_name = None

                def update_ui():
                    live.update(Panel(Markdown("".join(ui_buffer)), expand=False))

                stream = openai.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    stream=True,
                    tools=(
                        [to_openai_format(tool) for tool in self.tools]
                        if self.tools and tool_fail_count <= 1
                        else None
                    ),
                )

                for chunk in stream:
                    if chunk.choices[0].delta.tool_calls:
                        for function in [
                            tc.function for tc in chunk.choices[0].delta.tool_calls
                        ]:
                            if function.name == "Search":
                                tc_name = function.name
                            tc_arg_buffer.append(function.arguments)
                            try:
                                args = json.loads("".join(tc_arg_buffer))
                            except json.JSONDecodeError:
                                continue

                            ui_buffer.append(f"Running tool: {tc_name}\n {args}\n")
                            update_ui()

                            if tc_name == "Search":
                                ui_buffer.append("\nSearching the web...\n\n")
                                update_ui()
                                tool = next(
                                    (
                                        tool
                                        for tool in self.tools
                                        if tool.name == "Search"
                                    ),
                                    None,
                                )
                                if tool:
                                    tool_results["search"] = tool.run(**args)
                                    update_ui()
                                    if tool_results["search"].get("error"):
                                        tool_fail_count += 1
                                    else:
                                        tool_fail_count = 0
                                else:
                                    tool_fail_count += 1
                                    ui_buffer.append("Tool not found.\n")
                                    update_ui()

                    if chunk.choices[0].delta.content is not None:
                        buffer.append(chunk.choices[0].delta.content)
                        ui_buffer.append(chunk.choices[0].delta.content)
                        update_ui()

                    if chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason
                        break

                # Message buffer
                if buffer:
                    assistant_message = {
                        "role": "assistant",
                        "content": "".join(buffer),
                    }
                    self.messages.append(assistant_message)

                # Tool results buffer
                if tool_results:
                    tool_result_message = {
                        "role": "system",
                        "content": f"Tool results:\n{json.dumps(tool_results, indent=2)}\n\nPlease incorporate this information in your response.",
                    }
                    self.messages.append(tool_result_message)

                # Check if the chat is finished
                if finish_reason != "tool_calls":
                    if finish_reason != "stop":
                        rprint(
                            f"[red]Chat stopped unexpectedly. Reason: {finish_reason}[/red]"
                        )
                    break

            # Final response
            ui_buffer.append("\n\nFinal response:\n")
            ui_buffer.append(self.messages[-1]["content"])
            update_ui()

    def __str__(self):
        return f"ChatSession(chat_id={self.chat_id}, messages={self.messages})"

    def __repr__(self):
        return str(self)
