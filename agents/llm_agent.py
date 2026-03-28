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

    def _generate_with_fallback(self, client, contents: str):
        try:
            return client.models.generate_content(
                model=self.GEMINI_3_FLASH_PREVIEW,
                contents=contents
            )
        except Exception as e:
            err_str = str(e).upper()
            if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                self._log_debug(f"Model {self.GEMINI_3_FLASH_PREVIEW} unavailable. Stepping up to {self.GEMINI_3_1_PRO_PREVIEW} temporary fallback...")
                return client.models.generate_content(
                    model=self.GEMINI_3_1_PRO_PREVIEW,
                    contents=contents
                )
            raise

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

            accumulated = []
            iteration = 0
            max_iterations = 5

            while iteration < max_iterations:
                iteration += 1
                
                context_so_far = "\n\n".join(accumulated) if accumulated else "None"

                response = self._generate_with_fallback(
                    client,
                    contents=(
                        f"Original Goal:\n{context_description}\n\n"
                        f"Context Gathered So Far:\n{context_so_far}\n\n"
                        "Based on the Original Goal and the Context Gathered So Far, return a JSON array of AgentCommand definitions needed to gather the missing context. "
                        "Each element must be an object with 'command_name' and 'payload' keys. "
                        "Available commands: 'read_file' (payload needs 'path'), 'prompt_user' (payload needs 'question' to ask human for help). "
                        "When using the `prompt_user` command, you must formulate the `question` to be highly direct, concise, and conversational by asking exactly and only for the specific piece of missing information you need, rather than awkwardly dumping your entire multi-step internal reasoning checklist onto the human. "
                        "Return ONLY the raw JSON array with no markdown or code fences. "
                        "If you have gathered absolutely all the context needed to fulfill the original goal, or if you have hit a dead end and cannot proceed, you MUST logically return an empty JSON array: []"
                    )
                )

                try:
                    command_definitions = json.loads(response.text)
                    if not isinstance(command_definitions, list):
                        command_definitions = []
                except json.JSONDecodeError:
                    command_definitions = []

                if not command_definitions:
                    break

                for cmd_def in command_definitions:
                    cmd_name = cmd_def.get("command_name")
                    payload = cmd_def.get("payload", {})
                    
                    if cmd_name == "read_file":
                        path = payload.get("path", "")
                        read_cmd = AgentCommandFactory.read_file(path)
                        file_content = await self.issue_command(read_cmd)
                        accumulated.append(f"[File: {path}]\n{file_content}")
                    elif cmd_name == "prompt_user":
                        question = payload.get("question", "Human input required:")
                        self._log_debug(f"Initiating prompt_user: {question}")
                        prompt_cmd = AgentCommandFactory.prompt_user(payload)
                        user_reply = await self.issue_command(prompt_cmd)
                        accumulated.append(f"[User Reply to Prompt]\n{user_reply}")

            return "\n\n".join(accumulated)

        if command.command_name == "process_user_prompt":
            api_key = os.environ.get('GEMINI_API_KEY')
            client = genai.Client(api_key=api_key)
            prompt = command.payload.get("prompt", "")

            # Phase 1: ask LLM what context it needs
            phase1_response = self._generate_with_fallback(
                client,
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
            phase2_response = self._generate_with_fallback(
                client,
                contents=f"Context:\n{accumulated_context}\n\nQuestion:\n{prompt}"
            )
            return phase2_response.text

        return None
