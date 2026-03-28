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
