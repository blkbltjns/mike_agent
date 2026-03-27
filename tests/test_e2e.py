import pytest
from unittest.mock import patch

@patch('agents.llm_agent.LLMAgent.GEMINI_3_FLASH_PREVIEW', 'gemini-3.1-flash-lite-preview')
def test_e2e_live_simulation(capsys):
    import time
    from main import main
    from unittest.mock import patch
    
    # 1. Define the physical keystrokes we want the mock human to type into the terminal over time
    mock_inputs = [
        {"wait": 0.5, "input": "debug on"},
        {"wait": 0.5, "input": "enter_user_auto_mode"},
        {"wait": 2.0, "input": "Please read agent.py and tell me exactly how many imports it has at the top of the file."},
        {"wait": 20.0, "input": "Now list the exact names of the imported modules."},
        {"wait": 20.0, "input": "exit"},
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
        main()
        
    captured = capsys.readouterr()
    stdout = captured.out.lower()
    
    assert "--- entering auto mode ---" in stdout, "Mocked UserAgent did not enter auto mode"
    
    # Prove round 1 executed (something was printed by the agent)
    assert "based on" in stdout or "import" in stdout, "LLM failed to respond visually to prompt 1"
    
    # 3. LLM-as-a-judge evaluation of reasonableness
    from google import genai  # type: ignore
    client = genai.Client()
    eval_prompt = f"""
    You are an automated evaluator grading an AI agent E2E test.
    The agent was asked two questions sequentially in a stateless auto-mode loop:
    1. "Please read agent.py and tell me exactly how many imports it has at the top of the file."
    2. "Now list the exact names of the imported modules."
    
    Note: The auto mode is strictly architected to be stateless between rounds. Therefore, for question 2, it is entirely expected and correct for the agent to have forgotten we were discussing agent.py, and instead attempt to answer by reading project-level context like requirements.txt. 
    
    Here is the full captured output of the session, including the background debug logs tracing the context variables it fetched:
    <stdout_log>
    {captured.out}
    </stdout_log>
    
    Evaluate the agent's behavior. Did the agent successfully and tangibly read file(s) to gather context, and was its final answer to the user reasonable and factually dependent on the context it gathered?
    
    Respond strictly with exactly the word "YES" if the agent's behavior successfully proves the context-gathering capability was reasonable. Respond with "NO" and a brief explanation if it failed.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=eval_prompt
    )
    
    eval_result = response.text.strip().upper()
    assert "YES" in eval_result, f"LLM Evaluator failed the E2E run. Evaluation: {{response.text}}\nStdout: {{captured.out}}"
