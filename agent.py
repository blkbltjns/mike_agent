import time
from agent_command import AgentCommand

class Agent:
    """
    A single agent that polls the Bus for AgentCommands it owns,
    executes them in its own context, and writes results back to the Bus.
    """

    def __init__(self, command_names: list, command_registry, bus):
        self.command_names = command_names
        self.command_registry = command_registry
        self.bus = bus
        self.active = False

    def execute(self, command: AgentCommand):
        """
        Execute the given command.
        Must be implemented by subclasses to explicitly handle commands.
        """
        raise NotImplementedError("Subclasses must implement explicit command execution.")

    def _execute_next_command(self) -> bool:
        """
        Poll the Bus for one claimable AgentCommand, execute it, and write the result.
        Returns True if a command was processed, False if nothing was available.
        """
        command = self.bus.claim(self.command_names)
        if command is None:
            return False

        result = self.execute(command)
        
        agent_name = self.__class__.__name__
        self.bus.write_result(command.id, command.command_name, result, agent_name=agent_name)
        return True

    def run(self) -> None:
        """Run the agent loop continuously. Sleeps if no claimable commands."""
        self.active = True
        while self.active:
            processed = self._execute_next_command()
            if not processed:
                time.sleep(1)

    def stop(self) -> None:
        """Signals the infinite run loop to exit gracefully."""
        self.active = False
