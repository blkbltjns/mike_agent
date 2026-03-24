# GC Multi-Agent Coding Engine: Architecture & Vision

> **⚠️ IMPORTANT DIRECTIVE FOR AI AGENTS (ANTIGRAVITY OR OTHERS):**
> 1. **DO NOT MODIFY THIS FILE** unless explicitly instructed to do so by the user. This document serves as foundational context and a read-only architectural north star.
> 2. **THIS IS A WORK IN PROGRESS.** This document represents the current working theory of the architecture. Nothing is completely set in stone, and there are intentional holes and undefined edge cases that the user will solve during implementation. Do not assume this is a complete spec.

---

## 1. Core Vision & Philosophy
This system is being built to solve the severe limitations of current LLM coding tools (specifically shallow context gathering, relying on heuristics/naming conventions instead of tracing logic, and false confidence/hallucinations). 

**Key Tenets:**
* **Force Deep Investigation:** The system must definitively prove its understanding rather than making assumptions. 
* **Verifiable Audit Trail:** Every thought, action, and discovery must be recorded.
* **Deterministic Engine, Heuristic Brain:** Python handles the control flow, queues, and state. LLMs are used strictly for reasoning and deciding what command to issue next via structured outputs (JSON).
* **The User is an Agent:** Human-in-the-loop is treated not as an external interruption, but as just another peer agent processing tasks from the queue.

---

## 2. Core Infrastructure: The Message Bus
The system relies on a central `Bus` class that fully encapsulates the Inbox and Outbox. External components never interact with the Inbox or Outbox directly—they use the Bus's public API.

* **Bus Public API:** `enqueue(command)`, `claim(command_names)`, `write_result(request_id, command_name, result)`, `get_result(request_id)`.
* **The Global Inbox (Append-Only Task Queue):**
  * Contains pending `AgentCommand` objects (see Section 3).
  * **Append-Only:** Commands are never deleted from the Inbox. When an agent successfully claims a command, it is flagged as claimed but remains in the queue.
* **The Global Outbox (Append-Only Log):**
  * A permanent, chronological history of all completed commands and their results.
  * When an Inbox command is fulfilled, the result is appended here, permanently paired with its original `AgentCommand.id`.
  * **Append-Only:** Nothing is ever deleted. This is the system's absolute memory.

---

## 3. The Flat Command Pool & Routing
The system decouples *intent* (what needs to be done) from *execution* (who does it). 

* **AgentCommand:** The first-class data object representing a task. Each `AgentCommand` contains a unique `id`, a `command_name`, and a `payload` dictionary.
* **AgentCommandFactory:** A static-only factory class with bespoke static methods per command type (e.g., `AgentCommandFactory.say_hello()`). It is not instantiable. Its only job is to create and return typed `AgentCommand` objects. It does **not** enqueue them—the caller is responsible for passing the command to the `Bus`.
* **Passive Routing:** Agents do not talk to each other. A calling agent creates an `AgentCommand` and drops it into the Bus. Each agent symmetrically declares its `incoming_commands` (tasks it is registered to claim and process) and `outgoing_commands` (tasks it is authorized to construct and enqueue) during construction. Agents continuously use `threading` to asynchronously poll the Bus for matching incoming commands.

---

## 4. Agent Topology
All agents operate on the same basic loop: Poll Bus → Claim `AgentCommand` → Execute → Write result to Bus (or `sleep` if no matching commands). Agents expose a `stop()` method for graceful shutdown of the polling loop.

Crucially, **execution logic lives within the Agent context itself**. The definitions of what it actually means to `print("Hello")` or read from the user are methods inside the Agent object handling the command.

* **LLM Worker Agents:** Handle reasoning tasks (e.g., `formulate_plan`, `evaluate_code`). They output strictly formatted JSON containing their `thought` and a `next_command`.
* **Python Worker Agents (Deterministic):** Handle pure code/OS tasks (e.g., `read_file_contents`). No LLM needed.
* **The User Agent (Human):** The human literally acts as the "brain," registered identically to any other agent. Any command too complex for an LLM (e.g., `run_complex_build`, `prompt_user`) is mapped to the User Agent. The `UserAgent` operates via a synchronous polling terminal REPL. This robust design allows the human to proactively and autonomously type at any time—whether it's `view_incoming_commands` to read waiting background tasks, `reply` to fulfill a task, or `enqueue` to explicitly invoke new commands. The main program bootstraps the initial command, but the `UserAgent` remains a peer—not a special orchestrator.

---

## 5. Execution Flow & Cognitive Loop
The system runs as an autonomous, asynchronous `while` loop driven by Python. Each agent runs in its own `threading.Thread`.

1. **Initiation:** The LLMAgent specifically kicks off the system by issuing the first proactive target command down the system pipeline via a startup method.
2. **Processing:** Agents concurrently poll and claim `AgentCommand` objects they own from the Inbox.
3. **Async Outbox Tracking:** To achieve a perpetual linear goal, an agent constructs a new `AgentCommand` output, enqueues it to the Bus, and instantly assigns its generated `.id` internally to a state tracker (`waiting_for_results`).
4. **Resumption:** Agents autonomously parse the Outbox against their state tracker concurrently identically to Inbox polling. When the target Outbox resolution occurs, the agent consumes it via a routing continuation handler.
5. **Passive Termination:** The overarching loop concludes organically through `stop()` when logic thresholds dictate.

---

## 6. Known Gaps & WIP Areas (To Be Solved During Dev)
* **Outbox Result Schema:** The exact structure for Outbox result entries and LLM structured outputs are not yet fully defined. `AgentCommand` is now a first-class typed object, but the Outbox entries remain dictionaries.
* **Context Window Management:** As the Outbox grows permanently, how do we prevent blowing up the LLM context window? (e.g., summarization agents, semantic search over the Outbox).
* **Watchdog Interception:** The exact mechanics of how/if Watchdog LLMs monitor standard LLM outputs for infinite loops or hallucinations *before* they hit the outbox.