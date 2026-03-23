import threading
import time

from bus import Bus
from agent_command_registry import AgentCommandRegistry
from agent_command_factory import AgentCommandFactory
from agents import UserAgent, LLMAgent

def main():
    bus = Bus()
    command_registry = AgentCommandRegistry()

    # The agents register their commands back to the shared registry during __init__
    user_agent = UserAgent(command_registry=command_registry, bus=bus)
    llm_agent = LLMAgent(command_registry=command_registry, bus=bus)

    factory = AgentCommandFactory()

    # Start the agent loops in background threads
    threads = [
        threading.Thread(target=user_agent.run, daemon=True),
        threading.Thread(target=llm_agent.run, daemon=True)
    ]
    for thread in threads:
        thread.start()

    # Build typed commands via factory, then enqueue to bus
    cmd2 = factory.ask_user_agent({"question": "How are you doing today?"})
    cmd3 = factory.ask_llm_agent({"question": "What is the capital of France?"})

    bus.enqueue(cmd2)
    bus.enqueue(cmd3)

    # Poll until commands generate an entry in the outbox
    print("Waiting for agents to finish their tasks...")
    while True:
        r2 = bus.get_result(cmd2.id)
        r3 = bus.get_result(cmd3.id)

        if r2 is not None and r3 is not None:
            print("\nAll tasks completed:")
            print("ask_user_agent =>", r2["result"])
            print("ask_llm_agent =>", r3["result"])

            user_agent.stop()
            llm_agent.stop()
            break

        time.sleep(1)


if __name__ == "__main__":
    main()
