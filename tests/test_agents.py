import pytest
from unittest.mock import patch
from bus import Bus
from agents.user_agent import UserAgent
from agents.llm_agent import LLMAgent
from agent_command_factory import AgentCommandFactory

@pytest.fixture
def setup_components():
    bus = Bus()
    return bus

@patch('builtins.input', side_effect=['view_incoming_commands', 'list_commands', 'reply 1 Fine, thanks!', 'exit'])
def test_user_agent(mock_input, setup_components):
    bus = setup_components
    agent = UserAgent(bus=bus)
    
    cmd = AgentCommandFactory.prompt_user({"question": "How are you?"})
    bus.enqueue(cmd)
    
    agent.run()
    
    result = bus.get_result(cmd.id)
    assert result is not None
    assert result["result"] == "Fine, thanks!"

def test_llm_agent_tracker(setup_components):
    bus = setup_components
    agent = LLMAgent(bus=bus)
    
    # Simulate being bootstrapped by the main.py entrypoint
    cmd = AgentCommandFactory.prompt_user({"question": "Hello!"})
    bus.enqueue(cmd)
    agent.waiting_for_results[cmd.id] = {"action": "awaiting_user_reply"}    
    cmd = bus.claim(["prompt_user"])
    assert cmd is not None
    assert cmd.payload["question"] == "Hello!"
    
    bus.write_result(cmd.id, cmd.command_name, "I am an end user", "UserAgent")
    
    # This triggers the Outbox Tracker, routing the result back into handle_outbox_result
    agent._execute_next_command()
    
    next_cmd = bus.claim(["prompt_user"])
    assert next_cmd is not None
    assert "LLM parsed 'I am an end user'" in next_cmd.payload["question"]

@patch.dict('os.environ', {'GEMINI_API_KEY': 'fake_test_key'})
@patch('agents.llm_agent.genai.Client')
def test_llm_agent_gemini_integration(mock_client_class, setup_components):
    # Setup SDK mock to return a string resembling JSON
    mock_client_instance = mock_client_class.return_value
    mock_client_instance.models.generate_content.return_value.text = '{"mocked": "gemini_response"}'

    bus = setup_components
    agent = LLMAgent(bus=bus)
    
    # Create the incoming process_user_prompt command
    from agent_command import AgentCommand
    cmd = AgentCommand(command_name="process_user_prompt", payload={"prompt": "Hello"})
    bus.enqueue(cmd)
    
    # Process the command
    agent._execute_next_command()
    
    # 1. Verify Specification: SDK Integration and Environment keys
    mock_client_class.assert_called()
    mock_client_instance.models.generate_content.assert_called_with(
        model=agent.GEMINI_3_0_FLASH,
        contents="Hello You must return ONLY a raw JSON dictionary without any markdown formatting or code blocks."
    )
    
    # 2. Verify Specification: strict JSON dictionary formatting output
    result_item = bus.get_result(cmd.id)
    assert result_item is not None
    assert isinstance(result_item["result"], dict)
    assert result_item["result"] == {"mocked": "gemini_response"}
