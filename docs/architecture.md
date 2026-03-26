# System Architecture

## 1. Core Infrastructure: The Message Bus
The system relies on a central `Bus` class that fully encapsulates the Inbox and Outbox. External components never interact with the Inbox or Outbox directly—they use the Bus's public API.

* **Bus Public API:** `broadcast_to_one(command)`, `broadcast_to_all(command)`, `claim(command_names, agent_id)`, `write_result(request_id, command_name, result, agent_name)`, `get_result(request_id)`.
* **The Global Inbox (Append-Only Task Queue):**
  * Contains pending `AgentCommand` objects.
  * **Append-Only:** Commands are never deleted from the Inbox. The Bus internally tracks which single-target commands have been claimed. Claimed commands remain in the queue but are skipped by subsequent `claim()` calls.
* **The Global Outbox (Append-Only Log):**
  * A permanent, chronological history of all completed commands and their results.
  * When an Inbox command is fulfilled, the result is appended here, permanently paired with its original `AgentCommand.id` (as `request_id`).
  * **Append-Only:** Nothing is ever deleted. This is the system's absolute memory.

## 2. The Flat Command Pool & Routing
The system decouples *intent* (what needs to be done) from *execution* (who does it). 

* **AgentCommand:** The first-class data object representing a task. Each `AgentCommand` contains a unique `id`, a `command_name`, and a `payload` dictionary. AgentCommand is a plain data class with no subtyping and no claim state — routing semantics are determined entirely by the Bus method used to submit it.
* **AgentCommandFactory:** A static-only factory class with bespoke static methods per command type. It is not instantiable. Its only job is to create and return typed `AgentCommand` objects. It does **not** enqueue them—the caller is responsible for passing the command to the `Bus`.
* **Passive Routing:** Agents do not talk to each other. A calling agent creates an `AgentCommand` and submits it to the Bus via `broadcast_to_one` (single-target, claimable by exactly one agent) or `broadcast_to_all` (visible to every agent, never consumed). Each agent declares its `incoming_commands` during construction. Agents continuously use `threading` to asynchronously poll the Bus for matching incoming commands. The Bus tracks per-agent delivery of `broadcast_to_all` commands internally. When `claim()` is called with an `agent_id`, the Bus records that this agent has received a given broadcast and will not return it again on future calls.

## 3. Agent Topology
All agents operate on the same basic loop: Poll Bus → Claim `AgentCommand` → Execute → Write result to Bus. Each agent instance is assigned a globally unique `id` at construction time. Agents expose a `stop()` method for graceful shutdown. Execution logic lives within the Agent context itself.

* `handle_command` is an `async` method on all agents. Each agent's thread hosts its own `asyncio` event loop via `asyncio.run()`. This allows a command handler to `await` the inline execution of dependent sub-commands without blocking other agents.
* **LLM Worker Agents:** Handle reasoning tasks. The LLMAgent claims and executes `process_user_prompt` and `gather_context` commands. For `process_user_prompt`, execution is two-phase: Phase 1 calls the LLM with the user's prompt, instructing it to respond in natural text describing what context it needs before it can answer. That natural text is enqueued as the payload of a `gather_context` command, which the LLMAgent immediately claims and executes inline via `await`. Phase 2 uses the gathered context — the LLMAgent prepends the accumulated context to the original prompt and makes a second LLM call to produce the final answer. For `gather_context`, the LLMAgent calls the LLM with the natural text description of needed context, instructing it to return a JSON array of tool commands. The LLMAgent executes each tool command sequentially, accumulates the results, and writes the cumulative output to the Outbox as the `gather_context` result.
* **The User Agent (Human):** Registered identically to any other agent. The `UserAgent` operates via a synchronous polling terminal REPL, allowing the human to proactively and autonomously type (`view_incoming_commands`, `reply`, `enqueue`, `list_commands`, `enter_user_auto_mode`, `exit`). The `enter_user_auto_mode` command is a self-routed command that the UserAgent both enqueues and handles, entering a streamlined dialogue loop that automates the claim/reply cycle with the LLM agent.
* **System Observability & Global Broadcasts:** The Base Agent intercepts and handles specific system configuration broadcasts (like `toggle_debug_logging`) directly within its core polling loop. This enables a unified, inherited mechanism for all agents to output debug tracing to the terminal and a shared file, seamlessly decoupling this observable behavior from subclass logic.

## 4. Execution Flow & Cognitive Loop
The system runs as an autonomous, asynchronous `while` loop driven by Python. Each agent runs in its own `threading.Thread`.

1. **Initiation:** The system starts with an empty Bus. Agents may seed the Bus either programmatically via optional `bootstrap_commands` passed to an agent's `run` method during thread startup, or organically through agent execution (e.g., the UserAgent entering auto mode from the REPL). Bootstrap commands are submitted via `broadcast_to_one`.
2. **Processing:** Agents concurrently poll and claim `AgentCommand` objects they own from the Inbox.
3. **Async Outbox Tracking:** An agent constructs a new `AgentCommand` output, enqueues it to the Bus, and instantly assigns its generated `.id` internally to a state tracker (`waiting_for_results`).
4. **Resumption:** Agents autonomously parse the Outbox against their state tracker concurrently. When the target Outbox resolution occurs, the agent consumes it via a routing continuation handler.
5. **Passive Termination:** The overarching loop concludes organically through `stop()`.