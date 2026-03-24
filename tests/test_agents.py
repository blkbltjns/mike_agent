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

@patch.object(LLMAgent, 'execute', return_value={"response": "I am the mocked Gemini response!"})
def test_llm_agent_tracker(mock_execute, setup_components):
    bus = setup_components
    agent = LLMAgent(bus=bus)
    
    # Simulate being bootstrapped by the main.py entrypoint
    cmd = AgentCommandFactory.prompt_user({"question": "Hello!"})
    bus.enqueue(cmd)
    agent.waiting_for_results.add(cmd.id)    
    cmd = bus.claim(["prompt_user"])
    assert cmd is not None
    assert cmd.payload["question"] == "Hello!"
    
    bus.write_result(cmd.id, cmd.command_name, "I am an end user", "UserAgent")
    
    # Tick 1: Outbox triggers handle_outbox_result, enqueues process_user_prompt, and the inbox immediately claims it and calls mocked execute()
    agent._execute_next_command()
    
    assert mock_execute.call_count == 1
    
    # Tick 2: Outbox triggers handle_outbox_result with the mocked Gemini response, enqueues prompt_user
    agent._execute_next_command()
    
    final_cmd = bus.claim(["prompt_user"])
    assert final_cmd is not None
    assert final_cmd.payload["question"] == "I am the mocked Gemini response!"
    assert final_cmd.id in agent.waiting_for_results

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
        model=agent.GEMINI_3_FLASH_PREVIEW,
        contents="Hello You must return ONLY a raw JSON dictionary without any markdown formatting or code blocks. The dictionary must contain exactly one key named 'response' carrying your conversational reply or question."
    )
    
    # 2. Verify Specification: strict JSON dictionary formatting output
    result_item = bus.get_result(cmd.id)
    assert result_item is not None
    assert isinstance(result_item["result"], dict)
    assert result_item["result"] == {"mocked": "gemini_response"}

def test_live_gemini_integration_loop(setup_components):
    import os
    from dotenv import load_dotenv
    # Ensure variables are mapped for live API execution
    load_dotenv()
    
    bus = setup_components
    agent = LLMAgent(bus=bus)
    
    # 1. Downgrade to verified cheapest model for live tests
    agent.GEMINI_3_FLASH_PREVIEW = agent.GEMINI_3_1_FLASH_LITE
    
    # 2. Bootstrap system with a prompt wait
    initial_cmd = AgentCommandFactory.prompt_user({"question": "Say exactly 'ping'."})
    bus.enqueue(initial_cmd)
    agent.waiting_for_results.add(initial_cmd.id)
    
    # Claim it so it doesn't stay unhandled 
    bus.claim(["prompt_user"])
    
    # 3. Simulate human reacting directly back to the outbox
    bus.write_result(initial_cmd.id, initial_cmd.command_name, "Please reply exactly with the word 'ping', and nothing else", "MockUserAgent")
    
    # 4. First tick: outbox routes human text into a `process_user_prompt` command
    # execute() sweeps it immediately and queries the real live Google APIs
    agent._execute_next_command()
    
    # 5. Second tick: outbox mapping generates a generic conversational `prompt_user` command
    agent._execute_next_command()
    
    # 6. Verify completion
    next_question_cmd = bus.claim(["prompt_user"])
    assert next_question_cmd is not None
    assert "question" in next_question_cmd.payload
    
    answer_text = next_question_cmd.payload["question"].lower()
    assert "ping" in answer_text, f"Gemini did not respond with 'ping', got instead: {answer_text}"

@patch('agents.llm_agent.LLMAgent.GEMINI_3_FLASH_PREVIEW', 'gemini-3.1-flash-lite-preview')
def test_e2e_live_simulation(capsys):
    import time
    from main import main
    from unittest.mock import patch
    
    # 1. Define the physical keystrokes we want the mock human to type into the terminal over time
    mock_inputs = [
        # Wait half a sec for LLMAgent daemon thread to bootstrap its command, then pull from bus
        {"wait": 0.5, "input": "view_incoming_commands"},
        # Reply to the bootstrapped task ID 1
        {"wait": 0.1, "input": "reply 1 Please reply exactly with the word 'ping', and nothing else."},
        # Hold typing for 4 seconds so the daemon thread has time to contact Google APIs and write back
        {"wait": 4.0, "input": "view_incoming_commands"},
        # Shutdown
        {"wait": 0.1, "input": "exit"}
    ]
    
    input_state = {"index": 0}
    def mock_input_func(prompt=""):
        if input_state["index"] >= len(mock_inputs):
            return "exit"
        
        instruction = mock_inputs[input_state["index"]]
        input_state["index"] += 1
        
        time.sleep(float(instruction["wait"]))
        return str(instruction["input"])
        
    with patch("builtins.input", side_effect=mock_input_func):
        # 2. Run the actual application entrypoint directly.
        # This spins up the LLMAgent natively, meaning it relies on .env and hits live endpoints.
        main()
        
    captured = capsys.readouterr()
    stdout = captured.out.lower()
    
    # 3. Assertions proving routing success
    assert "handled command 1." in stdout, "Mocked UserAgent did not correctly process the human reply"
    
    # Prove the LLM thread successfully resolved the network API logic and emitted the answer
    assert "ping" in stdout, f"E2E wait window ended before Gemini replied with 'ping', output was: {stdout}"
