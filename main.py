import threading
import time

from bus import Bus
from agent_command_factory import AgentCommandFactory
from agents import UserAgent, LLMAgent

def main():
    bus = Bus()

    # The agents register their commands back to the shared registry during __init__
    user_agent = UserAgent(bus=bus)
    llm_agent = LLMAgent(bus=bus)

    # Start background agents in daemon threads
    llm_thread = threading.Thread(target=llm_agent.run, daemon=True)
    llm_thread.start()

    # The LLMAgent natively initializes the workflow loop completely autonomously
    llm_agent.initiate_conversation("How can I start helping you today?")

    # The UserAgent handles standard input, which is blocking and not fully thread-safe.
    # By running its loop on the main thread, it safely captures input and keeps the app alive.
    try:
        user_agent.run()
    except KeyboardInterrupt:
        print("\nShutting down main loop...")
        user_agent.stop()
        llm_agent.stop()


if __name__ == "__main__":
    main()
