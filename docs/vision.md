# Core Vision & Philosophy

This system is being built to solve the severe limitations of current LLM coding tools (specifically shallow context gathering, relying on heuristics/naming conventions instead of tracing logic, and false confidence/hallucinations). 

**Key Tenets:**
* **Force Deep Investigation:** The system must definitively prove its understanding rather than making assumptions. 
* **Verifiable Audit Trail:** Every thought, action, and discovery must be recorded.
* **Deterministic Engine, Heuristic Brain:** Python handles the control flow, queues, and state. LLMs are used strictly for reasoning and deciding what command to issue next via structured outputs (JSON).
* **The User is an Agent:** Human-in-the-loop is treated not as an external interruption, but as just another peer agent processing tasks from the queue.