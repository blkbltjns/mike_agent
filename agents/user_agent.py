from agent import Agent

class UserAgent(Agent):
    """
    An agent that processes user-related tasks in its own executable context.
    """
    def __init__(self, command_registry, bus):
        super().__init__(command_names=["ask_user_agent"], command_registry=command_registry, bus=bus)
        self.command_registry.register("ask_user_agent", self.__class__.__name__)

    def execute(self, command):
        """Explicitly execute commands this agent claims."""
        if command.command_name == "ask_user_agent":
            return self.handle_ask_user_agent(command.payload)
        return None

    def handle_ask_user_agent(self, payload: dict = None) -> str:
        """Prompts the user via commandline with a question."""
        if payload is None:
            payload = {}
        question = payload.get("question", "What is your input?")
        answer = input(f"{question} ")
        return answer
