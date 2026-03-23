from agent import Agent

class LLMAgent(Agent):
    """
    An agent that processes LLM-related tasks in its own context.
    """
    def __init__(self, command_registry, bus):
        super().__init__(command_names=["ask_llm_agent"], command_registry=command_registry, bus=bus)
        self.command_registry.register("ask_llm_agent", self.__class__.__name__)

    def execute(self, command):
        """Explicitly execute commands this agent claims."""
        if command.command_name == "ask_llm_agent":
            return self.handle_ask_llm_agent(command.payload)
        return None

    def handle_ask_llm_agent(self, payload: dict = None) -> str:
        """Stub that reads the question and returns 'you asked: xyz'."""
        if payload is None:
            payload = {}
        question = payload.get("question", "")
        return f"you asked: {question}"
