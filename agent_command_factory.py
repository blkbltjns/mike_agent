from agent_command import AgentCommand

class AgentCommandFactory:
    """A factory that constructs typed AgentCommand objects for agents to execute. Not instantiable."""
    
    def __init__(self):
        raise TypeError("AgentCommandFactory is not meant to be instantiated. Use its static methods directly.")

    @staticmethod
    def prompt_user(payload: dict = None) -> AgentCommand:
        return AgentCommand("prompt_user", payload)

    @staticmethod
    def enter_user_auto_mode(payload: dict = None) -> AgentCommand:
        return AgentCommand("enter_user_auto_mode", payload)

    @staticmethod
    def process_user_prompt(payload: dict = None) -> AgentCommand:
        return AgentCommand("process_user_prompt", payload)

    @staticmethod
    def read_file(path: str) -> AgentCommand:
        return AgentCommand("read_file", {"path": path})

    @staticmethod
    def gather_context(payload: dict = None) -> AgentCommand:
        return AgentCommand("gather_context", payload)

    @classmethod
    def get_all_commands(cls) -> list:
        return ["prompt_user", "process_user_prompt", "enter_user_auto_mode", "read_file", "gather_context"]
