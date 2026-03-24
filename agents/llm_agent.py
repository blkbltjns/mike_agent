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
    def __init__(self, bus):
        all_cmds = AgentCommandFactory.get_all_commands()
        super().__init__(incoming_commands=["process_user_prompt"], outgoing_commands=all_cmds, bus=bus)

    def initiate_conversation(self, initial_question: str):
        """Manually push the first prompt_user task to the Bus and track it."""
        cmd = AgentCommandFactory.prompt_user({"question": initial_question})
        self.bus.enqueue(cmd)
        self.waiting_for_results[cmd.id] = {"action": "awaiting_user_reply"}

    def handle_outbox_result(self, result: dict, context: dict):
        """Reacts autonomously when the human formally replies to a tracked prompt."""
        if context.get("action") == "awaiting_user_reply":
            user_text = result.get("result", "")
            
            # Format our LLM reasoning...
            next_question = f"LLM parsed '{user_text}'. Tell me more."
            
            # Autonomously fire the NEXT question down the pipe to maintain the Q&A loop
            cmd = AgentCommandFactory.prompt_user({"question": next_question})
            self.bus.enqueue(cmd)
            self.waiting_for_results[cmd.id] = {"action": "awaiting_user_reply"}

    def execute(self, command):
        if command.command_name == "process_user_prompt":
            api_key = os.environ.get('GEMINI_API_KEY')
            client = genai.Client(api_key=api_key)
            prompt = command.payload.get("prompt", "")
            
            # Enforce that the LLM returns JSON by appending a rigid instruction
            instruction = " You must return ONLY a raw JSON dictionary without any markdown formatting or code blocks."
            full_prompt = prompt + instruction
            
            response = client.models.generate_content(
                model='gemini-3.0-flash', 
                contents=full_prompt
            )
            
            # Guarantee the final execution payload is formatted strictly as a JSON dictionary
            try:
                result_dict = json.loads(response.text)
                return result_dict
            except json.JSONDecodeError:
                # Fallback to satisfy our structural wrapper specification constraint
                return {"error": "Failed to parse JSON", "raw_output": response.text}
            
        return None
