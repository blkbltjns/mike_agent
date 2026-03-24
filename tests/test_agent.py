import pytest
import threading
import time
from bus import Bus
from agent import Agent
from agent_command import AgentCommand

class DummyAgent(Agent):
    """A minimal subclass used purely for unit testing the base Agent loop."""
    def __init__(self, bus):
        super().__init__(incoming_commands=["dummy_command"], bus=bus)

    def execute(self, command):
        if command.command_name == "dummy_command":
            return self.handle_dummy_command(command.payload)

    def handle_dummy_command(self, payload: dict = None) -> str:
        return "Dummy Result"

def make_system():
    """Helper to wire up a fresh bus and dummy agent."""
    bus = Bus()
    agent = DummyAgent(bus=bus)
    return bus, agent


class TestAgentExecuteNextCommand:
    def test_returns_false_when_empty(self):
        bus, agent = make_system()
        result = agent._execute_next_command()
        assert result is False

    def test_returns_true_when_processed(self):
        bus, agent = make_system()
        bus.enqueue(AgentCommand("dummy_command"))
        result = agent._execute_next_command()
        assert result is True

    def test_claims_command_from_bus(self):
        bus, agent = make_system()
        bus.enqueue(AgentCommand("dummy_command"))
        agent._execute_next_command()
        assert bus.claim(["dummy_command"]) is None

    def test_writes_result_to_outbox(self):
        bus, agent = make_system()
        cmd = AgentCommand("dummy_command")
        bus.enqueue(cmd)
        agent._execute_next_command()
        assert bus.get_result(cmd.id) is not None

    def test_outbox_refs_command(self):
        bus, agent = make_system()
        cmd = AgentCommand("dummy_command")
        bus.enqueue(cmd)
        agent._execute_next_command()
        entry = bus.get_result(cmd.id)
        assert entry["request_id"] == cmd.id
        assert entry["command_name"] == "dummy_command"
        assert entry["agent_name"] == "DummyAgent"

    def test_ignores_unowned_command(self):
        bus, agent = make_system()
        bus.enqueue(AgentCommand("some_other_command"))
        result = agent._execute_next_command()
        assert result is False
        assert bus.claim(["some_other_command"]) is not None


class TestAgentThreadLoop:
    def test_run_processes_all_commands_in_background(self):
        bus, agent = make_system()
        cmd1 = AgentCommand("dummy_command")
        cmd2 = AgentCommand("dummy_command")
        
        bus.enqueue(cmd1)
        bus.enqueue(cmd2)
        
        t = threading.Thread(target=agent.run)
        t.start()
        
        while bus.get_result(cmd2.id) is None:
            time.sleep(0.01)
            
        agent.stop()
        t.join(timeout=2.0)
        
        assert bus.claim(["dummy_command"]) is None
        assert bus.get_result(cmd1.id) is not None
        assert bus.get_result(cmd2.id) is not None

    def test_run_bootstraps_commands(self):
        bus, agent = make_system()
        # Use an unowned command so it enters the tracker but isn't instantly processed and deleted
        cmd = AgentCommand("unowned_command")
        
        t = threading.Thread(
            target=agent.run, 
            kwargs={"bootstrap_commands": [(cmd, {"test": "context_data"})]}
        )
        t.start()
        
        # Verify the command hit the bus by claiming it manually (since agent doesn't own it)
        fetched_cmd = None
        while fetched_cmd is None:
            fetched_cmd = bus.claim(["unowned_command"])
            time.sleep(0.01)
            
        agent.stop()
        t.join(timeout=2.0)
        
        # Verify the context was recorded
        assert cmd.id in agent.waiting_for_results
        assert agent.waiting_for_results[cmd.id] == {"test": "context_data"}

class TestDummyContext:
    def test_dummy_command_returns_result(self):
        bus, agent = make_system()
        result = agent.handle_dummy_command()
        assert result == "Dummy Result"
