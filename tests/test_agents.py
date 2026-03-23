import pytest
from unittest.mock import patch
from bus import Bus
from agent_command_registry import AgentCommandRegistry
from agents import UserAgent, LLMAgent
from agent_command_factory import AgentCommandFactory

@pytest.fixture
def setup_components():
    command_registry = AgentCommandRegistry()
    bus = Bus()
    factory = AgentCommandFactory()
    return command_registry, bus, factory

@patch('builtins.input', return_value='Fine, thanks!')
def test_user_agent(mock_input, setup_components):
    command_registry, bus, factory = setup_components
    agent = UserAgent(command_registry=command_registry, bus=bus)
    
    cmd = factory.ask_user_agent({"question": "How are you?"})
    bus.enqueue(cmd)
    
    agent._execute_next_command()
    
    mock_input.assert_called_once_with("How are you? ")
    
    result = bus.get_result(cmd.id)
    assert result is not None
    assert result["result"] == "Fine, thanks!"

def test_llm_agent(setup_components):
    command_registry, bus, factory = setup_components
    agent = LLMAgent(command_registry=command_registry, bus=bus)
    
    cmd = factory.ask_llm_agent({"question": "1+1?"})
    bus.enqueue(cmd)
    
    agent._execute_next_command()
    
    result = bus.get_result(cmd.id)
    assert result is not None
    assert result["result"] == "you asked: 1+1?"
