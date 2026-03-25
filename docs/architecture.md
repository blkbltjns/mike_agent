# System Architecture

## 1. Core Infrastructure: The Message Bus
The system relies on a central `Bus` class that fully encapsulates the Inbox and Outbox. External components never interact with the Inbox or Outbox directly—they use the Bus's public API.

* **Bus Public API:** `enqueue(command)`, `claim(command_names)`, `write_result(request_id, command_name, result, agent_name)`, `get_result(request_id)`.
* **The Global Inbox (Append-Only Task Queue):**
  * Contains pending `AgentCommand` objects.
  * **Append-Only:** Commands are never deleted from the Inbox. When an agent successfully claims a command, it is flagged as claimed but remains in the queue.
* **The Global Outbox (Append-Only Log):**
  * A permanent, chronological history of all completed commands and their results.
  * When an Inbox command is fulfilled, the result is appended here, permanently paired with its original `AgentCommand.id` (as `request_id`).
  * **Append-Only:** Nothing is ever deleted. This is the system's absolute memory.

## 2. The Flat Command Pool & Routing
The system decouples *intent* (what needs to be done) from *execution* (who does it). 

* **AgentCommand:** The first-class data object representing a task. Each `AgentCommand` contains a unique `id`, a `command_name`, and a `payload` dictionary.
* **AgentCommandFactory:** A static-only factory class with bespoke static methods per command type. It is not instantiable. Its only job is to create and return typed `AgentCommand` objects. It does **not** enqueue them—the caller is responsible for passing the command to the `Bus`.
* **Passive Routing:** Agents do not talk to each other. A calling agent creates an `AgentCommand` and drops it into the Bus. Each agent declares its `incoming_commands` during construction. Agents have universal access to enqueue any valid command, and continuously use `threading` to asynchronously poll the Bus for matching incoming commands.

## 3. Agent Topology
All agents operate on the same basic loop: Poll Bus → Claim `AgentCommand` → Execute → Write result to Bus. Agents expose a `stop()` method for graceful shutdown. Execution logic lives within the Agent context itself.

* **LLM Worker Agents:** Handle reasoning tasks. Output strictly formatted JSON. The LLMAgent may act as its own tool executor. When its LLM response signals a tool call, the agent enqueues that command to the Bus, registers its ID in `waiting_for_results`, then claims and executes the command itself — writing the result to the Outbox. Reasoning resumes once the Outbox result is available. This preserves the full audit trail through the Bus while keeping tool execution under the LLMAgent's jurisdiction. `read_file` is the first defined tool command, with a payload containing a `path` string.
* **The User Agent (Human):** Registered identically to any other agent. The `UserAgent` operates via a synchronous polling terminal REPL, allowing the human to proactively and autonomously type (`view_incoming_commands`, `reply`, `enqueue`, `list_commands`, `enter_user_auto_mode`, `exit`). The `enter_user_auto_mode` command is a self-routed command that the UserAgent both enqueues and handles, entering a streamlined dialogue loop that automates the claim/reply cycle with the LLM agent.

## 4. Execution Flow & Cognitive Loop
The system runs as an autonomous, asynchronous `while` loop driven by Python. Each agent runs in its own `threading.Thread`.

1. **Initiation:** The system starts with an empty Bus. Agents may seed the Bus either programmatically via optional `bootstrap_commands` passed to an agent's `run` method during thread startup, or organically through agent execution (e.g., the UserAgent entering auto mode from the REPL).
2. **Processing:** Agents concurrently poll and claim `AgentCommand` objects they own from the Inbox.
3. **Async Outbox Tracking:** An agent constructs a new `AgentCommand` output, enqueues it to the Bus, and instantly assigns its generated `.id` internally to a state tracker (`waiting_for_results`).
4. **Resumption:** Agents autonomously parse the Outbox against their state tracker concurrently. When the target Outbox resolution occurs, the agent consumes it via a routing continuation handler.
5. **Passive Termination:** The overarching loop concludes organically through `stop()`.