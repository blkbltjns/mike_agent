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
* **Passive Routing:** Agents do not talk to each other. A calling agent creates an `AgentCommand` and drops it into the Bus. Each agent symmetrically declares its `incoming_commands` and `outgoing_commands` during construction. Agents continuously use `threading` to asynchronously poll the Bus for matching incoming commands.

## 3. Agent Topology
All agents operate on the same basic loop: Poll Bus → Claim `AgentCommand` → Execute → Write result to Bus. Agents expose a `stop()` method for graceful shutdown. Execution logic lives within the Agent context itself.

* **LLM Worker Agents:** Handle reasoning tasks. Output strictly formatted JSON.
* **The User Agent (Human):** Registered identically to any other agent. The `UserAgent` operates via a synchronous polling terminal REPL, allowing the human to proactively and autonomously type (`view_incoming_commands`, `reply`, `enqueue`, `list_commands`, `exit`).

## 4. Execution Flow & Cognitive Loop
The system runs as an autonomous, asynchronous `while` loop driven by Python. Each agent runs in its own `threading.Thread`.

1. **Initiation:** The LLMAgent specifically kicks off the system by issuing the first proactive target command.
2. **Processing:** Agents concurrently poll and claim `AgentCommand` objects they own from the Inbox.
3. **Async Outbox Tracking:** An agent constructs a new `AgentCommand` output, enqueues it to the Bus, and instantly assigns its generated `.id` internally to a state tracker (`waiting_for_results`).
4. **Resumption:** Agents autonomously parse the Outbox against their state tracker concurrently. When the target Outbox resolution occurs, the agent consumes it via a routing continuation handler.
5. **Passive Termination:** The overarching loop concludes organically through `stop()`.