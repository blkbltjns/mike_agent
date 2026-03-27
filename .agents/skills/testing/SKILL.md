---
name: testing
description: Standard operating procedure for executing the project's type checker and complete test suite
---

# Testing Procedures

1. **Pre-test Linting:** Before running the test suite, you must always run the type checker and fix any linting problems it finds. Execute it natively:
   `.\.venv\scripts\pyrefly.exe check .`
2. **Comprehensive Testing:** When running the test suite, always run the complete suite with no exclusions — including live API and end-to-end tests. Never filter out or skip tests when verifying correctness.
3. **Test Execution:** Execute tests natively in verbose output mode using your `run_command` tool. You do not need to redirect or parse text files; rely on the final summary block for pass/fail determination:
   `.\.venv\scripts\pytest.exe -v`
4. **E2E Debugging:** For end-to-end tests, you should use the built-in debug logging mechanism of the framework to do tracing.
