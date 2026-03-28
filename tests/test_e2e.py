import pytest
from unittest.mock import patch

@patch('agents.llm_agent.LLMAgent.GEMINI_3_FLASH_PREVIEW', 'gemini-3.1-flash-lite-preview')
def test_e2e_live_simulation(capsys):
    import time
    from main import main
    from unittest.mock import patch
    from google import genai  # type: ignore
    import os
    
    client = genai.Client()
    
    # 1. Provide the deterministic setup sequence
    setup_sequence = [
        {"wait": 0.5, "input": "debug on"},
        {"wait": 0.5, "input": "enter_user_auto_mode"},
        {"wait": 2.0, "input": "Read me all the code of my favorite app in the test_subject folder."}
    ]
    
    test_state = {"index": 0, "exiting": False}
    accumulated_stdout = []
    
    def mock_input_func(prompt=""):
        if test_state["exiting"]:
            return "exit"
            
        if test_state["index"] < len(setup_sequence):
            instruction = setup_sequence[test_state["index"]]
            test_state["index"] += 1
            time.sleep(float(instruction["wait"]))
            out, _ = capsys.readouterr()
            accumulated_stdout.append(out)
            return str(instruction["input"])
        
        # Dynamic conversational phase
        time.sleep(5.0)  # give the LLM agent time to generate and prompt the user
        out, _ = capsys.readouterr()
        accumulated_stdout.append(out)
        current_transcript = "".join(accumulated_stdout)
        
        fake_user_prompt = f"""
        You are the human user operating an AI assistant in an auto-mode conversational loop. 
        Your hidden context is that your absolutely favorite app is named "calculator.py".
        The AI is attempting to fulfill your original request: "Read me all the code of my favorite app in the test_subject folder."
        
        Here is the terminal transcript so far (including system debug traces):
        <transcript>
        {current_transcript}
        </transcript>
        
        Based on the transcript, the AI is waiting for your input at the prompt.
        If the AI is asking you a clarifying question (like what your favorite app is), answer it naturally and concisely.
        If the AI has successfully read the file and fully answered your original request, output EXACTLY the word "exit" to conclude the loop.
        If the AI is hopelessly stuck or hallucinated and did not gather the context properly, output EXACTLY the word "exit".
        
        Type your literal response below:
        """
        
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite-preview',
            contents=fake_user_prompt
        )
        fake_reply = response.text.strip()
        
        test_state["index"] += 1
        # Hard cap to prevent infinite loops (if the fake user and the assistant get stuck in a loop)
        if test_state["index"] > 10:
            test_state["exiting"] = True
            return "exit"
            
        if fake_reply.lower() == "exit":
            test_state["exiting"] = True
             
        return fake_reply
        
    with patch("builtins.input", side_effect=mock_input_func):
        main()
        
    out, _ = capsys.readouterr()
    accumulated_stdout.append(out)
    full_stdout = "".join(accumulated_stdout).lower()
    
    assert "--- entering auto mode ---" in full_stdout, "Mocked UserAgent did not enter auto mode"
    
    # Read architecture doc
    with open("docs/architecture.md", "r") as f:
        architecture_doc = f.read()
        
    eval_prompt = f"""
    You are an automated evaluator grading an AI agent E2E test.
    The goal of the test was to see if the system correctly recognized missing information, dynamically queried the human operator using a prompt_user command, acquired the answer ("calculator.py"), and then proceeded to gather context based on that new information. 
    
    The architecture demands that components like the LLMAgent do not hallucinate, but rather verifiably prove their understanding by issuing routing commands like "gather_context", "read_file", or "prompt_user". 
    
    Here is the architecture documentation:
    <architecture>
    {architecture_doc}
    </architecture>
    
    Here is the full captured output of the E2E session, including the background debug logs tracing the context variables it fetched and the dialogue from our Fake User LLM:
    <stdout_log>
    {full_stdout}
    </stdout_log>
    
    Evaluate the agent's behavior. Did the system successfully:
    1. Encounter the first prompt ("Read me all the code of my favorite app...")
    2. Halt and ask the user what their favorite app was (demonstrating anti-hallucination)?
    3. Receive the user's answer ("calculator.py")?
    4. Actively read the correct file and return a reasonable answer?
    
    Respond strictly with exactly the word "YES" if the agent's behavior successfully proves the context-gathering capability was reasonable and structurally sound. Respond with "NO" and a brief explanation if it failed.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=eval_prompt
    )
    
    eval_result = response.text.strip().upper()
    assert "YES" in eval_result, f"LLM Evaluator failed the E2E run. Evaluation: {{response.text}}\nStdout: {{full_stdout}}"
