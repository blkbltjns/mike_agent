import os
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
        super().__init__(incoming_commands=["process_user_prompt", "read_file"], bus=bus)

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
            llm_result = result.get("result", {})
            next_question = llm_result.get("response", str(llm_result))

            # Maintain the Q&A loop by actively asking the user the new question
            cmd = AgentCommandFactory.prompt_user({"question": next_question})
            self.bus.enqueue(cmd)
            self.waiting_for_results.add(cmd.id)

    def handle_command(self, command):
        if command.command_name == "read_file":
            path = command.payload.get("path", "")
            try:
                with open(path, "r") as f:
                    return f.read()
            except (FileNotFoundError, IOError) as e:
                return f"Error reading file: {e}"

        if command.command_name == "process_user_prompt":
            pass  # TODO: implement two-phase gather_context flow

        return None
