import argparse
from logging import basicConfig, getLogger

import openai
from dotenv import load_dotenv
from openai.types import Model
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from rich import print as rprint
from rich.console import Console
from rich.logging import RichHandler

from chat_cli.utils.manager import ChatSessionManager

load_dotenv()
console = Console()

basicConfig(level="ERROR", handlers=[RichHandler(console=console)])
getLogger("httpx").setLevel("WARNING")


def multi_line_prompt(prompt_text, completer=None):
    lines = []
    while True:
        if lines:
            prompt_text = " " * len(prompt_text)
        line = prompt(prompt_text, completer=completer, complete_while_typing=False)
        if line.endswith("\\"):
            lines.append(line[:-1])
        else:
            lines.append(line)
            break
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="OAI Playground")
    parser.add_argument("--version", action="version", version="0.1.0")
    parser.parse_args()

    session_manager = ChatSessionManager()
    session_manager.new_session()

    command_completer = WordCompleter(["?", "n", "l", "s", "d", "q", "t", "tl", "m"])

    try:
        while True:
            user_input = multi_line_prompt(
                "You (help: ?)> ", completer=command_completer
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
                    result = multi_line_prompt(
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
                    result = multi_line_prompt(
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
                        return model.id.startswith("gpt") and "instruct" not in model.id

                    models = filter(is_cc_model, openai.models.list())
                    completer = WordCompleter([model.id for model in models])
                    result = multi_line_prompt(
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
