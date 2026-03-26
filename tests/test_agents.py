import asyncio
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
    bus.broadcast_to_one(cmd)
    
    agent.run()
    
    result = bus.get_result(cmd.id)
    assert result is not None
    assert result["result"] == "Fine, thanks!"



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

    # We must patch get_result so that the synchronous while loop immediately finds an Outbox response to any process_user_prompt
    def mock_get_result(request_id):
        return {"result": f"LLM reply for {request_id}", "command_name": "process_user_prompt", "id": "msg_xyz"}
        
    with patch.object(bus, 'get_result', side_effect=mock_get_result):
        agent._enter_auto_mode()

    # Exhaust the bus claims
    commands = []
    while True:
        c = bus.claim(["process_user_prompt"], "test_manual")
        if not c:
            break
        commands.append(c)

    # Round 1: initial process_user_prompt must contain only the round 1 text
    assert len(commands) == 2
    assert commands[0].payload["prompt"] == "Hello round 1"
    assert "Hello round 2" not in commands[0].payload["prompt"]

    # Round 2: outbox result for prompt_cmd_1 must contain only the round 2 reply, not accumulated history
    assert commands[1].payload["prompt"] == "Hello round 2"
    assert "Hello round 1" not in commands[1].payload["prompt"]



def test_llm_agent_read_file_command(setup_components):
    """Spec Section 2 - read_file Command: the LLMAgent reads the file at the given path
    and writes the raw contents to the Outbox."""
    bus = setup_components
    agent = LLMAgent(bus=bus)

    test_file_path = "test_subject/utils.py"
    cmd = AgentCommandFactory.read_file(test_file_path)
    bus.broadcast_to_one(cmd)

    async def run_tick():
        await agent._execute_next_command()
        for t in list(agent._active_tasks):
            await t
    asyncio.run(run_tick())

    result = bus.get_result(cmd.id)
    assert result is not None

    with open(test_file_path, "r") as f:
        expected_content = f.read()

    assert result["result"] == expected_content

