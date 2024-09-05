import argparse
import openai
from openai.types import Model
from rich.console import Console
from rich.logging import RichHandler
from rich import print as rprint
from logging import basicConfig, getLogger
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from .chat import ChatSession
from dotenv import load_dotenv
import uuid

load_dotenv()
console = Console()

basicConfig(level="ERROR", handlers=[RichHandler(console=console)])
getLogger("httpx").setLevel("WARNING")


class ChatSessionManager:
    def __init__(self):
        self.sessions = {}
        self.current_session = None

    def new_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = ChatSession()
        self.current_session = session_id
        return session_id

    def get_current_session(self) -> ChatSession:
        return self.sessions.get(self.current_session)

    def list_sessions(self) -> list:
        return list(self.sessions.keys())

    def select_session(self, session_id) -> bool:
        if session_id in self.sessions:
            self.current_session = session_id
            return True
        return False

    def delete_session(self, session_id) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            if self.current_session == session_id:
                self.new_session()
            return True
        return False

    def toggle_tool(self) -> bool:
        current_session = self.get_current_session()
        if current_session:
            current_session.enable_tool = not current_session.enable_tool
            return current_session.enable_tool
        return False

    def change_model(self, model):
        current_session = self.get_current_session()
        if current_session:
            current_session.model = model


def main():
    parser = argparse.ArgumentParser(description="OAI Playground")
    parser.add_argument("--version", action="version", version="0.1.0")
    parser.add_argument("--config", help="Path to the configuration file")
    args = parser.parse_args()

    session_manager = ChatSessionManager()
    session_manager.new_session()

    command_completer = WordCompleter(["?", "n", "l", "s", "d", "q", "t", "tl", "m"])

    try:
        while True:
            user_input = prompt(
                "You (help: ?)> ",
                completer=command_completer,
                complete_while_typing=False,
            )
            match user_input:
                case "q":
                    break
                case "?":
                    rprint("Available commands:")
                    rprint("? - Show this help")
                    rprint("n - New conversation")
                    rprint("l - List conversations")
                    rprint("s - Select conversation")
                    rprint("d - Delete conversation")
                    rprint("t - Toggle tools")
                    rprint("tl - List loaded tools")
                    rprint("m - Change model")
                    rprint("q - Quit")
                case "n":
                    session_id = session_manager.new_session()
                    console.clear()
                    rprint(f"Created new session: {session_id}")
                case "l":
                    sessions = session_manager.list_sessions()
                    rprint("Available sessions:")
                    for session_id in sessions:
                        if session_id == session_manager.current_session:
                            rprint(f"* {session_id} (current)")
                        else:
                            rprint(f"  {session_id}")
                case "s":
                    sessions = session_manager.list_sessions()
                    rprint("[bold]Available sessions:[/bold]")
                    for session_id in sessions:
                        if session_id == session_manager.current_session:
                            rprint(f"* {session_id} (current)")
                        else:
                            rprint(f"  {session_id}")
                    completer = WordCompleter(sessions)
                    result = prompt(
                        "Enter the session ID to select: ", completer=completer
                    )
                    if result:
                        if session_manager.select_session(result):
                            rprint(f"Switched to session: {result}")
                        else:
                            rprint(f"Session not found: {result}")
                case "d":
                    sessions = session_manager.list_sessions()
                    rprint("[bold]Available sessions:[/bold]")
                    for session_id in sessions:
                        if session_id == session_manager.current_session:
                            rprint(f"* {session_id} (current)")
                        else:
                            rprint(f"  {session_id}")
                    completer = WordCompleter([*sessions])
                    result = prompt(
                        "\nEnter the session ID to delete: ", completer=completer
                    )
                    if result:
                        if session_manager.delete_session(result):
                            rprint(f"[green]Deleted session: {result}[/green]")
                        else:
                            rprint(f"[red]Session not found: {result}[/red]")

                case "t":
                    res = session_manager.toggle_tool()
                    if res:
                        rprint("Tools are now [green]enabled[/green]")
                    elif res is False:
                        rprint("Tools are now [red]disabled[/red]")

                case "tl":
                    rprint("Loaded tools:")
                    session = session_manager.get_current_session()
                    if session:
                        for tool in session.tools:
                            rprint(f"  {tool.name}")
                    else:
                        rprint("No active session.")

                case "m":

                    def is_cc_model(model: Model) -> bool:
                        return model.id.startswith("gpt") and not "instruct" in model.id

                    models = filter(is_cc_model, openai.models.list())
                    completer = WordCompleter([model.id for model in models])
                    result = prompt(
                        "Enter the model ID to switch (<Tab> to show list): ",
                        completer=completer,
                    )
                    if result:
                        session_manager.change_model(result)
                        rprint(f"Switched to model: {result}")

                case _:
                    if user_input.strip() == "":
                        rprint("[red]Empty input is not allowed.[/red]")
                        continue
                    current_session = session_manager.get_current_session()
                    if current_session:
                        res = current_session.send_message(
                            {"role": "user", "content": user_input},
                            console=console,
                        )
                    else:
                        rprint("No active session. Create a new one with 'n' command.")
    except KeyboardInterrupt:
        rprint("KeyboardInterrupt caught. Exiting...")


if __name__ == "__main__":
    main()
