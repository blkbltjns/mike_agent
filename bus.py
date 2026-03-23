import uuid
from agent_command import AgentCommand

class Inbox:
    """Mutable queue of pending AgentCommand objects."""
    def __init__(self):
        self._queue = []

    def enqueue(self, command: AgentCommand) -> AgentCommand:
        self._queue.append(command)
        return command

    def claim(self, command_names: list) -> AgentCommand | None:
        for cmd in self._queue:
            if not cmd.is_claimed and cmd.command_name in command_names:
                cmd.is_claimed = True
                return cmd
        return None

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def __len__(self):
        return len(self._queue)


class Outbox:
    """Append-only log of all completed AgentCommands and their results."""
    def __init__(self):
        self._log = []

    def append(self, request_id: str, command_name: str, result, agent_name: str = None) -> dict:
        entry = {
            "id": str(uuid.uuid4()),
            "request_id": request_id,
            "command_name": command_name,
            "result": result,
            "agent_name": agent_name
        }
        self._log.append(entry)
        return entry

    def items(self) -> list:
        return list(self._log)

    def __len__(self):
        return len(self._log)


class Bus:
    """Encapsulates the Inbox and Outbox logs, providing a public communication API for AgentCommands."""
    def __init__(self):
        self._inbox = Inbox()
        self._outbox = Outbox()

    def enqueue(self, command: AgentCommand) -> AgentCommand:
        return self._inbox.enqueue(command)

    def claim(self, command_names: list) -> AgentCommand | None:
        return self._inbox.claim(command_names)

    def write_result(self, request_id: str, command_name: str, result, agent_name: str = None) -> dict:
        return self._outbox.append(request_id, command_name, result, agent_name)

    def get_result(self, request_id: str) -> dict | None:
        """Scan the outbox for the completed request_id and return the item if found."""
        for item in self._outbox.items():
            if item["request_id"] == request_id:
                return item
        return None
