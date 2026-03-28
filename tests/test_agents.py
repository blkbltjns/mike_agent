import asyncio
import pytest
from unittest.mock import patch, MagicMock, mock_open, AsyncMock
from bus import Bus
from agents.user_agent import UserAgent
from agents.llm_agent import LLMAgent
from agent_command_factory import AgentCommandFactory

@pytest.fixture
def setup_components():
    bus = Bus()
    return bus

def test_user_agent(setup_components):
    bus = setup_components
    agent = UserAgent(bus=bus)
    
    cmd = AgentCommandFactory.prompt_user({"question": "How are you?"})
    bus.broadcast_to_one(cmd)
    
    async def run_tick():
        agent.active = True
        
        with patch('builtins.input', return_value="Fine, thanks!"):
            result = await agent._handle_command(cmd)
        
        # Write the result to the bus so the test validation passes
        bus.write_result(cmd.id, cmd.command_name, result, "UserAgent")
            
    asyncio.run(run_tick())
    
    result = bus.get_result(cmd.id)
    assert result is not None
    assert result["result"] == "Fine, thanks!"




def test_user_agent_auto_mode_stateless(setup_components):
    """Spec Section 5 - Auto Mode Loop: Each round is stateless; the human's input for
    each turn must be passed as a fresh, isolated prompt with no accumulated history."""
    bus = setup_components
    agent = UserAgent(bus=bus)
    agent.active = True

    async def mock_issue_command(command):
        # We need to artificially return an outbound LLM response so the auto-loop drops to the next turn immediately
        import asyncio
        await asyncio.sleep(0.01) # tiny realistic yield
        # Record command natively so the test assertions below can read from it!
        bus.broadcast_to_one(command)
        return f"LLM reply for {command.id}"
        
    with patch.object(agent, 'issue_command', side_effect=mock_issue_command):
        cmd = AgentCommandFactory.enter_user_auto_mode()
        
        async def run_tick():
            with patch('builtins.input', side_effect=["Hello round 1", "Hello round 2", "exit"]):
                await agent._handle_command(cmd)
                
        asyncio.run(run_tick())

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

def test_llm_agent_fallback_on_503(setup_components):
    """Spec Section 4 - Temporary Model Step-Up Contract: LLMAgent steps up to PRO model
    if it encounters an UNAVAILABLE error."""
    bus = setup_components
    agent = LLMAgent(bus=bus)

    mock_error = Exception("503 UNAVAILABLE: Server overloaded")
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        mock_error,
        MagicMock(text="[]")
    ]

    with patch('os.environ.get', return_value="FAKE_KEY"):
        with patch('google.genai.Client', return_value=mock_client):
            cmd = AgentCommandFactory.gather_context({"text": "test"})
            bus.broadcast_to_one(cmd)
            
            async def run_tick():
                await agent._execute_next_command()
                for t in list(agent._active_tasks):
                    await t
            asyncio.run(run_tick())

            assert mock_client.models.generate_content.call_count == 2
            call_1 = mock_client.models.generate_content.call_args_list[0]
            call_2 = mock_client.models.generate_content.call_args_list[1]
            
            assert call_1.kwargs["model"] == agent.GEMINI_3_FLASH_PREVIEW
            assert call_2.kwargs["model"] == agent.GEMINI_3_1_PRO_PREVIEW


def test_gather_context_exits_on_empty_array(setup_components):
    """Spec Section 4 - gather_context Handler: loop terminates immediately when LLM returns []."""
    bus = setup_components
    agent = LLMAgent(bus=bus)

    mock_response = MagicMock()
    mock_response.text = "[]"

    async def run():
        with patch('google.genai.Client'):
            with patch.object(agent, '_generate_with_fallback', return_value=mock_response) as mock_gen:
                with patch.object(agent, 'issue_command', new_callable=AsyncMock) as mock_issue:
                    cmd = AgentCommandFactory.gather_context({"text": "what files do I need?"})
                    result = await agent._handle_command(cmd)
                    assert mock_gen.call_count == 1
                    mock_issue.assert_not_called()
                    assert result == ""

    asyncio.run(run())


def test_gather_context_hard_cap_at_5_iterations(setup_components):
    """Spec Section 4 - gather_context Handler: loop runs at most 5 iterations regardless of LLM output."""
    bus = setup_components
    agent = LLMAgent(bus=bus)

    mock_response = MagicMock()
    mock_response.text = '[{"command_name": "read_file", "payload": {"path": "foo.py"}}]'

    async def run():
        with patch('google.genai.Client'):
            with patch.object(agent, '_generate_with_fallback', return_value=mock_response) as mock_gen:
                with patch.object(agent, 'issue_command', new_callable=AsyncMock, return_value="fake content"):
                    cmd = AgentCommandFactory.gather_context({"text": "gather everything"})
                    await agent._handle_command(cmd)
                    assert mock_gen.call_count == 5

    asyncio.run(run())


def test_gather_context_issues_subcommand_and_accumulates(setup_components):
    """Spec Section 4 - gather_context Handler: each sub-command is dispatched via issue_command and its result is accumulated."""
    bus = setup_components
    agent = LLMAgent(bus=bus)

    responses = [
        MagicMock(text='[{"command_name": "read_file", "payload": {"path": "utils.py"}}]'),
        MagicMock(text="[]"),
    ]

    async def run():
        with patch('google.genai.Client'):
            with patch.object(agent, '_generate_with_fallback', side_effect=responses):
                with patch.object(agent, 'issue_command', new_callable=AsyncMock, return_value="file content here") as mock_issue:
                    cmd = AgentCommandFactory.gather_context({"text": "I need utils.py"})
                    result = await agent._handle_command(cmd)
                    assert result is not None
                    assert mock_issue.call_count == 1
                    assert "file content here" in result

    asyncio.run(run())


def test_gather_context_accumulates_multiple_commands(setup_components):
    """Spec Section 4 - gather_context Handler: results from multiple sub-commands in one iteration are all concatenated."""
    bus = setup_components
    agent = LLMAgent(bus=bus)

    responses = [
        MagicMock(text='[{"command_name": "read_file", "payload": {"path": "a.py"}}, {"command_name": "prompt_user", "payload": {"question": "Which module?"}}]'),
        MagicMock(text="[]"),
    ]
    issue_returns = ["content of a.py", "the user said: module X"]

    async def run():
        with patch('google.genai.Client'):
            with patch.object(agent, '_generate_with_fallback', side_effect=responses):
                with patch.object(agent, 'issue_command', new_callable=AsyncMock, side_effect=issue_returns):
                    cmd = AgentCommandFactory.gather_context({"text": "I need context"})
                    result = await agent._handle_command(cmd)
                    assert result is not None
                    assert "content of a.py" in result
                    assert "the user said: module X" in result

    asyncio.run(run())


def test_gather_context_handles_malformed_json_gracefully(setup_components):
    """Spec Section 4 - gather_context Handler: malformed LLM JSON output is treated as [] and the loop exits cleanly."""
    bus = setup_components
    agent = LLMAgent(bus=bus)

    mock_response = MagicMock()
    mock_response.text = "this is definitely not json"

    async def run():
        with patch('google.genai.Client'):
            with patch.object(agent, '_generate_with_fallback', return_value=mock_response):
                with patch.object(agent, 'issue_command', new_callable=AsyncMock) as mock_issue:
                    cmd = AgentCommandFactory.gather_context({"text": "I need context"})
                    result = await agent._handle_command(cmd)
                    mock_issue.assert_not_called()
                    assert result == ""

    asyncio.run(run())
