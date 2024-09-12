import logging
import subprocess

from pydantic import BaseModel, Field

from ..utils.tool_loader import BaseTool

logger = logging.getLogger(__name__)


class ShellCommandSchema(BaseModel):
    command: str = Field(
        ..., title="Command", description="The shell command to execute."
    )
    confirmation: bool = Field(
        ..., title="Confirmation", description="User confirmation to execute command."
    )


class ShellCommandTool(BaseTool):
    name = "ShellCommand"
    description = "Execute shell commands with confirmation using Rich prompt. \nYou should take user's confirmation before executing the command."
    schema = ShellCommandSchema

    def run(self, **kwargs) -> dict:
        try:
            command = kwargs.get("command")
            if not command:
                return {"error": "No command provided."}

            if not kwargs.get("confirmation"):
                return {
                    "error": "You need to take user's confirmation to execute command."
                }

            try:
                result = subprocess.run(
                    command, shell=True, check=True, capture_output=True, text=True
                )

                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
            except subprocess.CalledProcessError as e:
                return {
                    "error": f"Command execution failed: {str(e)}",
                    "stdout": e.stdout,
                    "stderr": e.stderr,
                    "returncode": e.returncode,
                }
        except Exception as e:
            logger.warning(f"Command execution failed: {str(e)}")
            return {
                "error": f"Command execution failed: {str(e)}",
                "stdout": "",
                "stderr": "",
                "returncode": 1,
            }

    async def arun(self, **kwargs) -> dict:
        return self.run(**kwargs)
