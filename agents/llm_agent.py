import os
import json
from google import genai  # type: ignore
from agent import Agent
from agent_command_factory import AgentCommandFactory
from agent_command import AgentCommand

class LLMAgent(Agent):
    """
    An agent that processes LLM-related tasks and proactively guides the User.
    """
    # Verified Gemini Model IDs (as of March 2026)
    GEMINI_3_FLASH_PREVIEW = 'gemini-3-flash-preview'          # verified
    GEMINI_3_1_PRO_PREVIEW = 'gemini-3.1-pro-preview'          # verified
    GEMINI_2_5_FLASH = 'gemini-2.5-flash'                      # verified
    GEMINI_2_5_PRO = 'gemini-2.5-pro'                          # verified
    GEMINI_3_1_FLASH_LITE = 'gemini-3.1-flash-lite-preview'    # verified

    def __init__(self, bus):
        super().__init__(incoming_commands=["process_user_prompt", "gather_context", "read_file"], bus=bus)

    async def _handle_command(self, command: AgentCommand):
        if command.command_name == "read_file":
            path = command.payload.get("path", "")
            try:
                with open(path, "r") as f:
                    return f.read()
            except (FileNotFoundError, IOError) as e:
                return f"Error reading file: {e}"

        if command.command_name == "gather_context":
            api_key = os.environ.get('GEMINI_API_KEY')
            client = genai.Client(api_key=api_key)
            context_description = command.payload.get("text", "")

            response = client.models.generate_content(
                model=self.GEMINI_3_FLASH_PREVIEW,
                contents=(
                    f"{context_description}\n"
                    "Return a JSON array of AgentCommand definitions needed to gather this context. "
                    "Each element must be an object with 'command_name' and 'payload' keys. "
                    "Available commands: 'read_file' (payload needs 'path'), 'prompt_user' (payload needs 'question' to ask human for help). "
                    "Return ONLY the raw JSON array with no markdown or code fences. "
                    "Example: [{\"command_name\": \"read_file\", \"payload\": {\"path\": \"path/to/file\"}}]"
                )
            )

            try:
                command_definitions = json.loads(response.text)
                if not isinstance(command_definitions, list):
                    command_definitions = []
            except json.JSONDecodeError:
                command_definitions = []

            accumulated = []
            for cmd_def in command_definitions:
                command_name = cmd_def.get("command_name")
                payload = cmd_def.get("payload", {})
                
                if command_name == "read_file":
                    path = payload.get("path", "")
                    read_cmd = AgentCommandFactory.read_file(path)
                    file_content = await self.issue_command(read_cmd)
                    accumulated.append(f"[File: {path}]\n{file_content}")
                elif command_name == "prompt_user":
                    prompt_cmd = AgentCommandFactory.prompt_user(payload)
                    user_reply = await self.issue_command(prompt_cmd)
                    accumulated.append(f"[User Reply to Prompt]\n{user_reply}")

            return "\n\n".join(accumulated)

        if command.command_name == "process_user_prompt":
            api_key = os.environ.get('GEMINI_API_KEY')
            client = genai.Client(api_key=api_key)
            prompt = command.payload.get("prompt", "")

            # Phase 1: ask LLM what context it needs
            phase1_response = client.models.generate_content(
                model=self.GEMINI_3_FLASH_PREVIEW,
                contents=(
                    f"{prompt}\n"
                    "Before answering, describe in natural language what files or context "
                    "you would need to read to give a complete answer."
                )
            )
            context_description = phase1_response.text

            # Suspend and gather context elegantly
            gather_cmd = AgentCommandFactory.gather_context({"text": context_description})
            accumulated_context = await self.issue_command(gather_cmd)

            # Phase 2: call LLM with context prepended
            phase2_response = client.models.generate_content(
                model=self.GEMINI_3_FLASH_PREVIEW,
                contents=f"Context:\n{accumulated_context}\n\nQuestion:\n{prompt}"
            )
            return phase2_response.text

        return None
