# Component Specifications & Testing Contract

> **Note:** This document, along with the rest of the `docs/` directory, is the immutable source of truth for component behaviors, expected inputs/outputs, and edge-case handling. All unit tests must explicitly target a rule defined in this directory. Do not update this document to reflect the code; update the code to reflect this document.

## 1. The Message Bus
* **Initialization:** The Bus must encapsulate private instances of `Inbox` and `Outbox` internally.
* **Inbox Behavior:**
  * Must generate globally unique identifiers for each enqueued `AgentCommand`.
  * Cannot be popped from. Queued items are flagged as `is_claimed` internally upon claim.
  * Cannot double-claim. An already claimed command must return `None` to subsequent `claim()` attempts.
* **Outbox Behavior:**
  * Retains a persistent list of dictionary elements, strictly structured as: `{"request_id": str, "command_name": str, "result": Any, "agent_name": str}`.
  * Must return `None` when `get_result()` queries an unknown ID.

## 2. Agent Commands
* **Data Object Contract:** Must encapsulate a unique string `id`, a string `command_name`, a boolean `is_claimed`, and a dictionary `payload`.
* **Factory Responsibilities:** `AgentCommandFactory` must contain isolated class/static methods that construct completely valid typed `AgentCommand` objects. The Factory never connects to the Bus.
* **`read_file` Command:** The `read_file` command payload must contain a `path` string. The LLMAgent, upon claiming a `read_file` command it has enqueued, reads the file at that path and writes the raw contents as a string to the Outbox, paired with the original command ID.

## 3. Agent Execution Behavior Constraints
* **Validation Bounds:** Agents must strictly ignore commands in the Bus not present in their explicit `incoming_commands` list.
* **System Initialization:** Base Agents must accept an optional `bootstrap_commands` argument (a list of `AgentCommand` objects) in their `run` method. Prior to entering the polling loop, the agent must passively enqueue these commands to the Bus and register the command ID in its internal `waiting_for_results` state tracker.
* **Lifecycle Pipeline:**
  * Repeatedly poll the Bus inbox for matches across their `incoming_commands`.
  * Execute task.
  * Write the result directly back to the Bus Outbox, guaranteeing that `request_id` maps perfectly to the original claimed `AgentCommand.id`.
* **State Tracking and Resumption:** Agents tracking pending outbound operations via `waiting_for_results` must autonomously poll the Bus `Outbox`. When a response matching a tracked `request_id` arrives, the agent resumes execution logic processing the new dependency.

## 4. LLMAgent Execution Contract
* **LLM Integration:** The `LLMAgent` is explicitly responsible for executing tasks by querying the Gemini model using the `google-genai` SDK and the `GEMINI_API_KEY` environment variable. 
* **Verified Model Constraints:** The `LLMAgent` must use only verified Gemini model identifiers. All valid identifiers must be declared as named class constants on the `LLMAgent` (e.g., `GEMINI_3_FLASH_PREVIEW`, `GEMINI_3_1_PRO_PREVIEW`, `GEMINI_2_5_FLASH`, `GEMINI_2_5_PRO`, `GEMINI_3_1_FLASH_LITE`). Hardcoded model name strings outside of these constant declarations are forbidden.
* **JSON Output Formatting:** The `LLMAgent` must guarantee that all final execution payloads written back to the Bus Outbox are strictly formatted as valid dictionaries/JSON objects. The agent acts as a structural wrapper, ensuring formatting compliance regardless of the raw text shape returned by the underlying LLM API.
* **Stateless Prompt Execution:** The `LLMAgent` must treat every `process_user_prompt` command as a completely isolated, context-free API call. The `contents` field passed to the Gemini SDK must consist solely of the prompt string from the current command's payload, plus the JSON formatting instruction. The agent must never accumulate, prepend, or append prior conversation turns to the prompt. Each round is a fresh, single-turn call.
* **Tool Loop:** The LLMAgent must support a tool loop during prompt processing. If the Gemini response JSON contains a `tool` key, the agent treats it as an intermediate tool request and must not write a final result to the Outbox until all tool requests are resolved. The final result for the original `process_user_prompt` command is only written once the LLM produces a response containing no `tool` key.

## 5. User Agent Execution Contract
* **Synchronous REPL Loop:** The `UserAgent` represents a human operator. Unlike async background agents, it must operate a blocking, synchronous terminal interface.
* **Symmetrical Integration:** Even though it blocks the terminal, it must adhere identically to the core agent lifecycle by explicitly declaring `incoming_commands` and reading from/writing to the Bus.
* **Proactive & Reactive Capabilities:** The REPL must provide commands allowing the human to proactively `enqueue` new target commands, as well as reactively `reply` to matching commands waiting in the Inbox.
* **Auto Mode Loop:** When the UserAgent executes the `enter_user_auto_mode` command, it must enter a blocking, synchronous `while` loop that automates the claim/reply cycle. In this loop, it proactively prompts the user for their initial query and enqueues a `process_user_prompt` command. It then continuously polls its incoming commands for `prompt_user`, displays the question to the user, accepts synchronous terminal input, and writes the human's reply directly to the Outbox. It must also provide a mechanism for the user to type "exit" to break out of the auto mode loop back to the main REPL. Each round of auto mode is stateless. The human's input for each turn is passed to the LLMAgent as a fresh, isolated prompt with no accumulated conversation history from prior rounds.

## 6. Agent Dialogue Routing & Command Contracts
* **Dialogue Initiation (LLM agent to User agent):** The LLM agent must use the prompt_user command to request input from the human. The payload must strictly contain a `question` string.
* **Dialogue Response (Human to LLM agent):** The User agent handles prompt_user commands. The human reply is not routed as a new command, but must be written directly to the Bus Outbox as a result bound to the original command ID.
* **Passive Dialogue Continuation:** The LLM agent must use its internal waiting_for_results state tracker to asynchronously await the human reply to the prompt_user command in the Outbox before continuing its logic stream.
* **Live Dialogue Routing:** Upon receiving a tracked response to a `prompt_user` command from the Outbox, the LLM agent is strictly forbidden from echoing mocked strings. It must synthesize its next question by actively enqueuing a new `process_user_prompt` command containing the human's text back into the Message Bus. The agent must subsequently track this new command's ID to asynchronously capture the live Gemini JSON response before issuing the next `prompt_user` command.
* **System Bootstrapping Validation:** The system entrypoint must start with an empty Message Bus. The dialogue is initiated proactively by the human through the `enter_user_auto_mode` workflow, which seeds the first `process_user_prompt` command into the Bus for the LLMAgent to claim, triggering the automated back-and-forth cycle.
* **Proactive Execution (Human to LLM agent):** The human operator may autonomously instruct the system by instructing the User agent to enqueue a process_user_prompt command. The payload must strictly contain a `prompt` string.