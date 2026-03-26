import asyncio
import time
import uuid
from agent_command import AgentCommand

class Agent:
    """
    A single agent that polls the Bus for AgentCommands it owns,
    executes them in its own context, and writes results back to the Bus.
    """

    _shared_debug_file = None

    def __init__(self, incoming_commands: list, bus):
        self.id = str(uuid.uuid4())
        self.incoming_commands = list(incoming_commands)
        if "toggle_debug_logging" not in self.incoming_commands:
            self.incoming_commands.append("toggle_debug_logging")
        self.bus = bus
        self.active = False
        self.waiting_for_results = set()
        self._debug_enabled = False

    def _log_debug(self, msg: str):
        if not self._debug_enabled:
            return
        print(f"[DEBUG {self.__class__.__name__} {self.id[:8]}] {msg}")
        if Agent._shared_debug_file:
            try:
                with open(Agent._shared_debug_file, "a", encoding="utf-8") as f:
                    import datetime
                    f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{self.__class__.__name__} {self.id[:8]}] {msg}\n")
            except Exception:
                pass

    def _handle_debug_toggle(self, enabled: bool):
        if enabled and not self._debug_enabled:
            import datetime
            import os
            os.makedirs("logs", exist_ok=True)
            Agent._shared_debug_file = f"logs/debug_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            self._debug_enabled = True
            self._log_debug("Debug logging enabled.")
        elif not enabled and self._debug_enabled:
            self._log_debug("Debug logging disabled.")
            self._debug_enabled = False
            Agent._shared_debug_file = None

    async def handle_command(self, command: AgentCommand):
        """
        Handle the given command.
        Must be implemented by subclasses to explicitly handle commands.
        """
        raise NotImplementedError("Subclasses must implement explicit command handling.")

    def handle_outbox_result(self, result: dict):
        """
        Handle a tracked outbox result arriving back to the agent.
        Implemented by subclasses if they trace outbound commands.
        """
        pass

    def _check_waiting_results(self) -> bool:
        """Poll the Outbox for tracked commands safely without blocking."""
        for req_id in tuple(self.waiting_for_results):
            result_item = self.bus.get_result(req_id)
            if result_item is not None:
                self.handle_outbox_result(result_item)
                self.waiting_for_results.remove(req_id)
                return True

        return False

    async def _execute_next_command(self) -> bool:
        """
        First sweeps Outbox for tracked results, then polls Inbox for new commands.
        Returns True if any internal processing occurred.
        """
        processed_waiting = self._check_waiting_results()

        command = self.bus.claim(self.incoming_commands, self.id)
        if command is None:
            return processed_waiting

        if command.command_name == "toggle_debug_logging":
            self._handle_debug_toggle(command.payload.get("enabled", False))
            return True

        self._log_debug(f"Claimed command: {command.command_name} with payload: {command.payload}")
        result = await self.handle_command(command)

        if result is not None:
            self._log_debug(f"Finished command: {command.command_name} with result: {result}")
            agent_name = self.__class__.__name__
            self.bus.write_result(command.id, command.command_name, result, agent_name=agent_name)
        return True

    async def _async_run(self, bootstrap_commands: list = None) -> None:
        """The async main loop hosted inside the agent's thread."""
        if bootstrap_commands:
            for bt_cmd in bootstrap_commands:
                self.bus.broadcast_to_one(bt_cmd)
                self.waiting_for_results.add(bt_cmd.id)

        self.active = True
        while self.active:
            processed = await self._execute_next_command()
            if not processed:
                await asyncio.sleep(1)

    def run(self, bootstrap_commands: list = None) -> None:
        """Run the agent loop continuously inside an asyncio event loop."""
        asyncio.run(self._async_run(bootstrap_commands))

    def stop(self) -> None:
        """Signals the infinite run loop to exit gracefully."""
        self.active = False
