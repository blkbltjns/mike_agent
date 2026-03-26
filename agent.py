import asyncio
import time
from agent_command import AgentCommand

class Agent:
    """
    A single agent that polls the Bus for AgentCommands it owns,
    executes them in its own context, and writes results back to the Bus.
    """

    def __init__(self, incoming_commands: list, bus):
        self.incoming_commands = incoming_commands
        self.bus = bus
        self.active = False
        self.waiting_for_results = set()

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

        command = self.bus.claim(self.incoming_commands)
        if command is None:
            return processed_waiting

        result = await self.handle_command(command)

        if result is not None:
            agent_name = self.__class__.__name__
            self.bus.write_result(command.id, command.command_name, result, agent_name=agent_name)
        return True

    async def _async_run(self, bootstrap_commands: list = None) -> None:
        """The async main loop hosted inside the agent's thread."""
        if bootstrap_commands:
            for bt_cmd in bootstrap_commands:
                self.bus.enqueue(bt_cmd)
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
