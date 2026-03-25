import pytest
from unittest.mock import patch, MagicMock, mock_open
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
        contents="Hello" + agent.TOOL_INSTRUCTION
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
        # Enter auto mode loop
        {"wait": 0.5, "input": "enter_user_auto_mode"},
        # Provide initial prompt for round 1
        {"wait": 0.1, "input": "Please reply exactly with the word 'ping', and nothing else."},
        # Wait 4 seconds for LLM to answer round 1, then send round 2 prompt
        {"wait": 10.0, "input": "Please reply exactly with the word 'pong', and nothing else."},
        # Wait 4 seconds for LLM to answer round 2, then exit auto mode
        {"wait": 10.0, "input": "exit"},
        # Exit main REPL
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
    assert "--- entering auto mode ---" in stdout, "Mocked UserAgent did not enter auto mode"
    
    # Prove round 1: LLM replied with 'ping'
    assert "ping" in stdout, f"E2E wait window ended before Gemini replied with 'ping', output was: {stdout}"
    
    # Prove round 2: LLM replied with 'pong'
    assert "pong" in stdout, f"E2E wait window ended before Gemini replied with 'pong', output was: {stdout}"

@patch('builtins.input', side_effect=["Hello round 1", "Hello round 2", "exit"])
def test_user_agent_auto_mode_stateless(mock_input, setup_components):
    """Spec Section 5 - Auto Mode Loop: Each round is stateless; the human's input for
    each turn must be passed as a fresh, isolated prompt with no accumulated history."""
    bus = setup_components
    agent = UserAgent(bus=bus)
    agent.active = True

    # Pre-enqueue two prompt_user commands to give the auto mode loop responses to claim
    prompt_cmd_1 = AgentCommandFactory.prompt_user({"question": "LLM question 1?"})
    prompt_cmd_2 = AgentCommandFactory.prompt_user({"question": "LLM question 2?"})
    bus.enqueue(prompt_cmd_1)
    bus.enqueue(prompt_cmd_2)

    agent._enter_auto_mode()

    # Round 1: initial process_user_prompt must contain only the round 1 text
    initial_cmd = bus.claim(["process_user_prompt"])
    assert initial_cmd is not None
    assert initial_cmd.payload["prompt"] == "Hello round 1"
    assert "Hello round 2" not in initial_cmd.payload["prompt"]

    # Round 2: outbox result for prompt_cmd_1 must contain only the round 2 reply, not accumulated history
    result = bus.get_result(prompt_cmd_1.id)
    assert result is not None
    assert result["result"] == "Hello round 2"
    assert "Hello round 1" not in result["result"]

@patch.dict('os.environ', {'GEMINI_API_KEY': 'fake_test_key'})
@patch('agents.llm_agent.genai.Client')
def test_llm_agent_stateless_prompt_execution(mock_client_class, setup_components):
    """Spec Section 4 - Stateless Prompt Execution: every process_user_prompt command
    must be a completely isolated, context-free call to the Gemini SDK."""
    mock_client_instance = mock_client_class.return_value
    mock_client_instance.models.generate_content.return_value.text = '{"response": "mocked reply"}'

    bus = setup_components
    agent = LLMAgent(bus=bus)

    from agent_command import AgentCommand
    cmd1 = AgentCommand(command_name="process_user_prompt", payload={"prompt": "first prompt text"})
    cmd2 = AgentCommand(command_name="process_user_prompt", payload={"prompt": "second prompt text"})

    agent.execute(cmd1)
    agent.execute(cmd2)

    assert mock_client_instance.models.generate_content.call_count == 2

    call_1_contents = mock_client_instance.models.generate_content.call_args_list[0].kwargs["contents"]
    call_2_contents = mock_client_instance.models.generate_content.call_args_list[1].kwargs["contents"]

    # Each call must only contain its own prompt — no history from the other round
    assert "first prompt text" in call_1_contents
    assert "first prompt text" not in call_2_contents
    assert "second prompt text" in call_2_contents


def test_llm_agent_read_file_command(setup_components):
    """Spec Section 2 - read_file Command: the LLMAgent reads the file at the given path
    and writes the raw contents to the Outbox."""
    bus = setup_components
    agent = LLMAgent(bus=bus)

    test_file_path = "test_subject/utils.py"
    cmd = AgentCommandFactory.read_file(test_file_path)
    bus.enqueue(cmd)

    agent._execute_next_command()

    result = bus.get_result(cmd.id)
    assert result is not None

    with open(test_file_path, "r") as f:
        expected_content = f.read()

    assert result["result"] == expected_content


@patch('builtins.open', mock_open(read_data="fake file content"))
@patch.dict('os.environ', {'GEMINI_API_KEY': 'fake_test_key'})
@patch('agents.llm_agent.genai.Client')
def test_llm_agent_tool_loop(mock_client_class, setup_components):
    """Spec Section 4 - Tool Loop: the LLMAgent must not write a final result to the Outbox
    until all tool requests are resolved."""
    response_1 = MagicMock()
    response_1.text = '{"tool": "read_file", "path": "test_subject/utils.py"}'
    response_2 = MagicMock()
    response_2.text = '{"response": "the bug is in the range function"}'

    mock_client_instance = mock_client_class.return_value
    mock_client_instance.models.generate_content.side_effect = [response_1, response_2]

    bus = setup_components
    agent = LLMAgent(bus=bus)

    cmd = AgentCommandFactory.process_user_prompt({"prompt": "Find the bug."})
    bus.enqueue(cmd)

    # No result before processing
    assert bus.get_result(cmd.id) is None

    agent._execute_next_command()

    # Gemini must have been called exactly twice (once for tool detection, once for final answer)
    assert mock_client_instance.models.generate_content.call_count == 2

    # The final result must only be written after the full tool loop resolves
    result = bus.get_result(cmd.id)
    assert result is not None
    assert result["result"] == {"response": "the bug is in the range function"}
