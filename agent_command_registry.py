class AgentCommandRegistry:
    """Maps command names to the agents configured to execute them."""

    def __init__(self):
        self._map = {}  # command_name -> list of agent_names

    def register(self, command_name: str, agent_name: str) -> None:
        """Register an agent name as a capable handler for a given command name."""
        if command_name not in self._map:
            self._map[command_name] = []
        if agent_name not in self._map[command_name]:
            self._map[command_name].append(agent_name)

    def get_registered_agents(self, command_name: str) -> list:
        """Return the list of agent names registered for the given command name."""
        return self._map.get(command_name, [])

    def get_all_command_names(self) -> list:
        """Return all registered command names."""
        return list(self._map.keys())
