import uuid

class AgentCommand:
    """A first-class command representing a task request and its targeted payload."""
    def __init__(self, command_name: str, payload: dict = None):
        self.id = str(uuid.uuid4())
        self.command_name = command_name
        self.payload = payload or {}

    def __repr__(self):
        return f"<AgentCommand {self.id} | {self.command_name}>"
