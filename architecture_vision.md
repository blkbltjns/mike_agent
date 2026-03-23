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
* **The Global Inbox (Active Task Queue):**
  * Contains pending `AgentCommand` objects (see Section 3).
  * **Mutable:** When an agent successfully claims and processes a command, it is removed from the Inbox.
* **The Global Outbox (Append-Only Log):**
  * A permanent, chronological history of all completed commands and their results.
  * When an Inbox command is fulfilled, the result is appended here, permanently paired with its original `AgentCommand.id`.
  * **Immutable/Append-Only:** Nothing is ever deleted. This is the system's absolute memory.

---

## 3. The Flat Command Pool & Routing
The system decouples *intent* (what needs to be done) from *execution* (who does it). 

* **AgentCommand:** The first-class data object representing a task. Each `AgentCommand` contains a unique `id`, a `command_name`, and a `payload` dictionary.
* **AgentCommandFactory:** A factory class with bespoke static methods per command type (e.g., `AgentCommandFactory.say_hello()`). Its only job is to create and return typed `AgentCommand` objects. It does **not** enqueue them—the caller is responsible for passing the command to the `Bus`.
* **AgentCommandRegistry:** Maps command names to the agent handlers that execute them. A single command can be mapped to multiple agents, and a single agent mapped to multiple commands. Agents self-register the commands they support during `__init__`.
* **Passive Routing:** Agents do not talk to each other. A calling agent creates an `AgentCommand` and drops it into the Bus. Agents continuously use `threading` to asynchronously poll the Bus for commands they are mapped to.

---

## 4. Agent Topology
All agents operate on the same basic loop: Poll Bus → Claim `AgentCommand` → Execute → Write result to Bus (or `sleep` if no matching commands). Agents expose a `stop()` method for graceful shutdown of the polling loop.

Crucially, **execution logic lives within the Agent context itself**. The definitions of what it actually means to `print("Hello")` or read from the user are methods inside the Agent object handling the command.

* **GC (General Contractor) Agent:** The primary LLM orchestrator. Receives the initial prompt, ensures it understands, and enqueues initial high-level `AgentCommand` objects to the Bus.
* **LLM Worker Agents:** Handle reasoning tasks (e.g., `formulate_plan`, `evaluate_code`). They output strictly formatted JSON containing their `thought` and a `next_command`.
* **Python Worker Agents (Deterministic):** Handle pure code/OS tasks (e.g., `read_file_contents`). No LLM needed.
* **The User Agent (Human):** The human is registered as an agent in the system. Any command that is too complex for an LLM or Python right now (e.g., `run_complex_build`, `verify_hallucination`, `ask_user_clarification`) is simply mapped to the User Agent. The system prompts the human's terminal to fulfill the command, then seamlessly continues.

---

## 5. Execution Flow & Cognitive Loop
The system runs as an autonomous, asynchronous `while` loop driven by Python. Each agent runs in its own `threading.Thread`.

1. **Initiation:** User prompt is translated into initial `AgentCommand` objects (via `AgentCommandFactory`) and enqueued to the Bus.
2. **Processing:** Agents concurrently poll and claim `AgentCommand` objects they own from the Bus.
3. **Chained Execution:** To achieve a goal, an agent creates new `AgentCommand` objects and enqueues them to the Bus (e.g., to solve `fix_bug`, an agent enqueues a `read_file` command).
4. **Course Correction (No Deletions):** If an agent reviews an Outbox result and realizes it's wrong/insufficient, it does *not* delete it. It enqueues a *new* `AgentCommand`, referencing the failed Outbox ID, with instructions on why it failed and what to do next.
5. **Termination:** The loop concludes when the system's reasoning dictates the goal is met, enqueueing a `writeuserresponse` command. The mapped agent synthesizes the Outbox history and delivers the final answer. All agents are shut down via `stop()`.

---

## 6. Known Gaps & WIP Areas (To Be Solved During Dev)
* **Outbox Result Schema:** The exact structure for Outbox result entries and LLM structured outputs are not yet fully defined. `AgentCommand` is now a first-class typed object, but the Outbox entries remain dictionaries.
* **Context Window Management:** As the Outbox grows permanently, how do we prevent blowing up the LLM context window? (e.g., summarization agents, semantic search over the Outbox).
* **Watchdog Interception:** The exact mechanics of how/if Watchdog LLMs monitor standard LLM outputs for infinite loops or hallucinations *before* they hit the outbox.