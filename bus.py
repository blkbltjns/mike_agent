import uuid
import threading
from agent_command import AgentCommand


class Inbox:
    """Append-only queue of pending single-target AgentCommand objects."""
    def __init__(self):
        self._queue = []
        self._claimed_ids = set()
        self._lock = threading.Lock()

    def enqueue(self, command: AgentCommand) -> AgentCommand:
        with self._lock:
            self._queue.append(command)
            return command

    def claim(self, command_names: list) -> AgentCommand | None:
        with self._lock:
            for cmd in self._queue:
                if cmd.id not in self._claimed_ids and cmd.command_name in command_names:
                    self._claimed_ids.add(cmd.id)
                    return cmd
            return None

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0

    def __len__(self):
        with self._lock:
            return len(self._queue)


class BroadcastLog:
    """Append-only log of broadcast_to_all commands with per-agent delivery tracking."""
    def __init__(self):
        self._log = []
        self._delivered = {}  # {command_id: set of agent_ids that have received it}
        self._lock = threading.Lock()

    def append(self, command: AgentCommand) -> AgentCommand:
        with self._lock:
            self._log.append(command)
            self._delivered[command.id] = set()
            return command

    def claim(self, command_names: list, agent_id: str) -> AgentCommand | None:
        with self._lock:
            for cmd in self._log:
                if cmd.command_name in command_names and agent_id not in self._delivered.get(cmd.id, set()):
                    self._delivered[cmd.id].add(agent_id)
                    return cmd
            return None


class Outbox:
    """Append-only log of all completed AgentCommands and their results."""
    def __init__(self):
        self._log = []
        self._lock = threading.Lock()

    def append(self, request_id: str, command_name: str, result, agent_name: str | None = None) -> dict:
        with self._lock:
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
        with self._lock:
            return list(self._log)

    def __len__(self):
        with self._lock:
            return len(self._log)


class Bus:
    """Encapsulates the Inbox, BroadcastLog, and Outbox, providing a public communication API for AgentCommands."""
    def __init__(self):
        self._inbox = Inbox()
        self._broadcast_log = BroadcastLog()
        self._outbox = Outbox()

    def broadcast_to_one(self, command: AgentCommand) -> AgentCommand:
        """Submit a single-target command. Exactly one agent may claim it."""
        return self._inbox.enqueue(command)

    def broadcast_to_all(self, command: AgentCommand) -> AgentCommand:
        """Submit a broadcast command. Every agent may receive it exactly once."""
        return self._broadcast_log.append(command)

    def claim(self, command_names: list, agent_id: str) -> AgentCommand | None:
        """Claim a matching command. Checks single-target inbox first, then broadcast log."""
        cmd = self._inbox.claim(command_names)
        if cmd is not None:
            return cmd
        return self._broadcast_log.claim(command_names, agent_id)

    def write_result(self, request_id: str, command_name: str, result, agent_name: str | None = None) -> dict:
        return self._outbox.append(request_id, command_name, result, agent_name)

    def get_result(self, request_id: str) -> dict | None:
        """Scan the outbox for the completed request_id and return the item if found."""
        for item in self._outbox.items():
            if item["request_id"] == request_id:
                return item
        return None
