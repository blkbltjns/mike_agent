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
    GEMINI_3_1_PRO_PREVIEW = 'gemini-3.1-pro-preview' # verified
    GEMINI_2_5_FLASH = 'gemini-2.5-flash'          # verified
    GEMINI_2_5_PRO = 'gemini-2.5-pro'              # verified
    GEMINI_3_1_FLASH_LITE = 'gemini-3.1-flash-lite-preview' # verified

    def __init__(self, bus):
        super().__init__(incoming_commands=["process_user_prompt"], bus=bus)


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
            # Since Gemini returns a JSON dict, we assume we get a 'response' key based on instructions.
            next_question = llm_result.get("response", str(llm_result))
            
            # Maintain the Q&A loop by actively asking the user the new question
            cmd = AgentCommandFactory.prompt_user({"question": next_question})
            self.bus.enqueue(cmd)
            self.waiting_for_results.add(cmd.id)

    def execute(self, command):
        if command.command_name == "process_user_prompt":
            api_key = os.environ.get('GEMINI_API_KEY')
            client = genai.Client(api_key=api_key)
            prompt = command.payload.get("prompt", "")
            
            # Enforce that the LLM returns JSON by appending a rigid instruction
            instruction = " You must return ONLY a raw JSON dictionary without any markdown formatting or code blocks. The dictionary must contain exactly one key named 'response' carrying your conversational reply or question."
            full_prompt = prompt + instruction
            
            response = client.models.generate_content(
                model=self.GEMINI_3_FLASH_PREVIEW, 
                contents=full_prompt
            )
            
            # Guarantee the final execution payload is formatted strictly as a JSON dictionary
            try:
                result_dict = json.loads(response.text)
                self.waiting_for_results.add(command.id)
                return result_dict
            except json.JSONDecodeError:
                # Fallback to satisfy our structural wrapper specification constraint
                self.waiting_for_results.add(command.id)
                return {"error": "Failed to parse JSON", "raw_output": response.text}
            
        return None
