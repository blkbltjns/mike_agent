from agent_command import AgentCommand

class AgentCommandFactory:
    """A factory that constructs typed AgentCommand objects for agents to execute."""
    
    @staticmethod
    def ask_user_agent(payload: dict = None) -> AgentCommand:
        return AgentCommand("ask_user_agent", payload)

    @staticmethod
    def ask_llm_agent(payload: dict = None) -> AgentCommand:
        return AgentCommand("ask_llm_agent", payload)
