import os
import json
from google import genai
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

    def handle_outbox_result(self, result: dict):
        """Reacts autonomously when tracked prompts or processing commands resolve."""
        command_name = result.get("command_name")

        if command_name == "prompt_user":
            user_text = result.get("result", "")

            # Route human text to the real Gemini pipeline
            cmd = AgentCommand(command_name="process_user_prompt", payload={"prompt": user_text})
            self.bus.enqueue(cmd)
            self.waiting_for_results.add(cmd.id)

        elif command_name == "process_user_prompt":
            llm_text = result.get("result", "")

            # Maintain the Q&A loop by actively asking the user the new question
            cmd = AgentCommandFactory.prompt_user({"question": str(llm_text)})
            self.bus.enqueue(cmd)
            self.waiting_for_results.add(cmd.id)

    async def handle_command(self, command):
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
                    "Return a JSON array of tool commands needed to gather this context. "
                    "Each element must be an object with a 'tool' key. "
                    "Available tools: read_file (requires a 'path' key). "
                    "Return ONLY the raw JSON array with no markdown or code fences. "
                    "Example: [{\"tool\": \"read_file\", \"path\": \"path/to/file\"}]"
                )
            )

            try:
                tool_commands = json.loads(response.text)
                if not isinstance(tool_commands, list):
                    tool_commands = []
            except json.JSONDecodeError:
                tool_commands = []

            accumulated = []
            for tool_cmd_dict in tool_commands:
                if tool_cmd_dict.get("tool") == "read_file":
                    path = tool_cmd_dict.get("path", "")
                    read_cmd = AgentCommandFactory.read_file(path)
                    self.bus.enqueue(read_cmd)
                    claimed_read = self.bus.claim(["read_file"])
                    if claimed_read:
                        file_content = await self.handle_command(claimed_read)
                        self.bus.write_result(
                            claimed_read.id, claimed_read.command_name,
                            file_content, self.__class__.__name__
                        )
                        accumulated.append(f"[File: {path}]\n{file_content}")

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

            # Enqueue gather_context, claim and execute it inline
            gather_cmd = AgentCommandFactory.gather_context({"text": context_description})
            self.bus.enqueue(gather_cmd)
            claimed_gather = self.bus.claim(["gather_context"])
            accumulated_context = await self.handle_command(claimed_gather)
            self.bus.write_result(
                claimed_gather.id, claimed_gather.command_name,
                accumulated_context, self.__class__.__name__
            )

            # Phase 2: call LLM with context prepended
            phase2_response = client.models.generate_content(
                model=self.GEMINI_3_FLASH_PREVIEW,
                contents=f"Context:\n{accumulated_context}\n\nQuestion:\n{prompt}"
            )
            return phase2_response.text

        return None
