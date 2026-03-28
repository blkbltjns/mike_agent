from agent import Agent
from agent_command import AgentCommand
from agent_command_factory import AgentCommandFactory
import json

class UserAgent(Agent):
    """
    An agent that processes user-related tasks via an interactive concurrent REPL.
    """
    def __init__(self, bus):
        super().__init__(incoming_commands=["prompt_user", "enter_user_auto_mode"], bus=bus)
        import asyncio
        self._input_lock = asyncio.Lock()
        self._in_auto_mode = False

    async def get_human_input(self, prompt: str) -> str:
        """Helper to safely await human input collected by the unified REPL thread."""
        import asyncio
        self._log_debug("Explicit prompt method attempting to acquire input lock...")
        async with self._input_lock:
            self._log_debug("Explicit prompt method successfully acquired input lock.")
            print(f"\n[SYSTEM_PROMPT]: {prompt}\n(Type your response at the prompt below)>", flush=True)
            return await asyncio.to_thread(input)

    async def _repl_loop(self):
        """Asynchronous REPL loop that uniquely owns the stdin blocking thread."""
        import asyncio
        while self.active:
            try:
                if self._in_auto_mode:
                    await asyncio.sleep(0.1)
                    continue

                self._log_debug("Continuous background loop aggressively attempting to acquire input lock...")
                async with self._input_lock:
                    self._log_debug("Continuous background loop successfully acquired input lock.")
                    line = await asyncio.to_thread(input, "\nUserAgent> ")
                if not line.strip():
                    continue
                
                choice = line.strip()
                parts = choice.split(" ", 1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "enqueue":
                    self._handle_enqueue(arg)
                elif cmd == "list_commands":
                    self._list_commands()
                elif cmd == "enter_user_auto_mode":
                    self._in_auto_mode = True
                    auto_cmd = AgentCommandFactory.enter_user_auto_mode()
                    self.enqueue_command(auto_cmd)
                elif cmd == "exit" or cmd == "quit":
                    self.stop()
                elif cmd == "debug" and arg in ["on", "off"]:
                    enabled = (arg == "on")
                    toggle_cmd = AgentCommandFactory.toggle_debug_logging(enabled)
                    self.issue_broadcast_command(toggle_cmd)
                    print(f"Broadcasted toggle_debug_logging with enabled={enabled}")
                else:
                    print("Unknown command. Try: enqueue <command> <payload_json>, list_commands, enter_user_auto_mode, debug on/off")
            except (KeyboardInterrupt, EOFError):
                self.stop()
                print("\nExiting UserAgent loop.")

    async def _async_run(self, bootstrap_commands: list | None = None) -> None:
        self.active = True
        import asyncio
        repl_task = asyncio.create_task(self._repl_loop())
        self._active_tasks.add(repl_task)
        repl_task.add_done_callback(self._active_tasks.discard)
        await super()._async_run(bootstrap_commands)

    async def _handle_command(self, command: AgentCommand):
        """Handles single-target commands cleanly and natively inside the async task pipeline."""
        if command.command_name == "enter_user_auto_mode":
            try:
                print("\n--- Entering Auto Mode ---")
                initial_prompt = await self.get_human_input("Initial prompt (type 'exit' to leave auto mode)")
                if initial_prompt.lower() == 'exit':
                    print("--- Exiting Auto Mode ---")
                    return {"status": "exited"}

                process_cmd = AgentCommandFactory.process_user_prompt({"prompt": initial_prompt})
                print("Waiting for LLM reply...")
                result = await self.issue_command(process_cmd)

                while self.active:
                    print("\n[LLM_AGENT]: " + str(result))
                    reply = await self.get_human_input("Next prompt (type 'exit' to leave auto mode)")
                    if reply.lower() == 'exit':
                        print("--- Exiting Auto Mode ---")
                        break

                    new_cmd = AgentCommandFactory.process_user_prompt({"prompt": reply})
                    print("Waiting for LLM reply...")
                    result = await self.issue_command(new_cmd)

                return {"status": "exited"}
            finally:
                self._in_auto_mode = False

        elif command.command_name == "prompt_user":
            question = command.payload.get("question", "Human input required:")
            answer = await self.get_human_input(question)
            self._log_debug(f"User Response: {answer}")
            return answer

        return None

    def _list_commands(self):
        print("Commands you can explicitly enqueue:")
        for cmd in AgentCommandFactory.get_all_commands():
            print(f"  - {cmd}")

    def _handle_enqueue(self, arg: str):
        parts = arg.split(" ", 1)
        if not parts:
            print("Usage: enqueue <command_name> <payload_json>")
            return
            
        command_name = parts[0]
        payload = {}
        if len(parts) > 1:
            try:
                payload = json.loads(parts[1])
            except json.JSONDecodeError:
                print("Invalid JSON payload. Using empty dict.")
                payload = {}

        if command_name not in AgentCommandFactory.get_all_commands():
            print(f"Not a valid command: {command_name}.")
            return
            
        from agent_command import AgentCommand
        cmd = AgentCommand(command_name, payload)
        self.enqueue_command(cmd)
        print(f"Enqueued {command_name} with payload {payload}")
