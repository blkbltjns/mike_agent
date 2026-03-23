from agent_command_registry import AgentCommandRegistry

class TestAgentCommandRegistry:
    def test_register_and_get_registered_agents(self):
        registry = AgentCommandRegistry()
        registry.register("dummy_command", "Agent1")
        assert registry.get_registered_agents("dummy_command") == ["Agent1"]

    def test_get_registered_agents_returns_empty_list_for_unknown_command(self):
        registry = AgentCommandRegistry()
        assert registry.get_registered_agents("nonexistent") == []

    def test_get_all_command_names(self):
        registry = AgentCommandRegistry()
        registry.register("dummy1", "Agent1")
        registry.register("dummy2", "Agent1")
        names = registry.get_all_command_names()
        assert "dummy1" in names
        assert "dummy2" in names

    def test_registering_appends_agent_name(self):
        registry = AgentCommandRegistry()
        registry.register("dummy_command", "Agent1")
        registry.register("dummy_command", "Agent2")
        assert registry.get_registered_agents("dummy_command") == ["Agent1", "Agent2"]
    
    def test_registering_ignores_duplicates(self):
        registry = AgentCommandRegistry()
        registry.register("dummy_command", "Agent1")
        registry.register("dummy_command", "Agent1")
        assert registry.get_registered_agents("dummy_command") == ["Agent1"]
