from agent import Agent
from agent_command_factory import AgentCommandFactory
import json

class UserAgent(Agent):
    """
    An agent that processes user-related tasks via an interactive REPL.
    """
    def __init__(self, bus):
        super().__init__(incoming_commands=["prompt_user", "enter_user_auto_mode"], bus=bus)
        self.pending_tasks = {}
        self.task_counter = 1

    async def handle_command(self, command):
        """UserAgent handles commands via the REPL loop, not this pathway."""
        pass

    def run(self) -> None:
        """Override the base run loop to provide a synchronous REPL."""
        self.active = True
        while self.active:
            try:
                choice = input("\nUserAgent> ").strip()
                if not choice:
                    continue
                
                parts = choice.split(" ", 1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "view_incoming_commands":
                    self._view_incoming()
                elif cmd == "reply":
                    self._handle_reply(arg)
                elif cmd == "enqueue":
                    self._handle_enqueue(arg)
                elif cmd == "list_commands":
                    self._list_commands()
                elif cmd == "enter_user_auto_mode":
                    self._enter_auto_mode()
                elif cmd == "exit" or cmd == "quit":
                    self.stop()
                elif cmd == "debug" and arg in ["on", "off"]:
                    enabled = (arg == "on")
                    from agent_command_factory import AgentCommandFactory
                    toggle_cmd = AgentCommandFactory.toggle_debug_logging(enabled)
                    self.bus.broadcast_to_all(toggle_cmd)
                    print(f"Broadcasted toggle_debug_logging with enabled={enabled}")
                else:
                    print("Unknown command. Try: view_incoming_commands, reply <id> <text>, enqueue <command> <payload_json>, list_commands, enter_user_auto_mode, debug on/off")
            except (KeyboardInterrupt, EOFError):
                self.stop()
                print("\nExiting UserAgent loop.")

    def _view_incoming(self):
        # Sweeps bus for all incoming commands
        while True:
            command = self.bus.claim(self.incoming_commands, self.id)
            if not command:
                break
            self.pending_tasks[self.task_counter] = command
            self.task_counter += 1
            
        if not self.pending_tasks:
            print("No pending incoming commands.")
            return
            
        print("Pending Incoming Commands:")
        for task_id, command in self.pending_tasks.items():
            print(f"  [{task_id}] {command.command_name}: {command.payload}")

    def _list_commands(self):
        print("Commands you can explicitly enqueue:")
        for cmd in AgentCommandFactory.get_all_commands():
            print(f"  - {cmd}")

    def _handle_reply(self, arg: str):
        parts = arg.split(" ", 1)
        if len(parts) < 2:
            print("Usage: reply <id> <text>")
            return
            
        try:
            task_id = int(parts[0])
            answer = parts[1]
        except ValueError:
            print("Invalid ID format.")
            return
            
        if task_id not in self.pending_tasks:
            print(f"Task ID {task_id} not found pending.")
            return

        command = self.pending_tasks.pop(task_id)
        self.bus.write_result(command.id, command.command_name, answer, self.__class__.__name__)
        print(f"Handled command {task_id}.")

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
        self.bus.broadcast_to_one(cmd)
        print(f"Enqueued {command_name} with payload {payload}")

    def _enter_auto_mode(self):
        cmd = AgentCommandFactory.enter_user_auto_mode()
        self.bus.broadcast_to_one(cmd)
        
        claimed_cmd = None
        while claimed_cmd is None and self.active:
            claimed_cmd = self.bus.claim(["enter_user_auto_mode"], self.id)
            if not claimed_cmd:
                import time
                time.sleep(0.1)
                
        if not claimed_cmd:
            return
            
        print("\n--- Entering Auto Mode ---")
        initial_prompt = input("Initial prompt (type 'exit' to leave auto mode)> ").strip()
        if initial_prompt.lower() == 'exit':
            self.bus.write_result(claimed_cmd.id, claimed_cmd.command_name, {"status": "exited"}, self.__class__.__name__)
            print("--- Exiting Auto Mode ---")
            return
            
        process_cmd = AgentCommandFactory.process_user_prompt({"prompt": initial_prompt})
        self.bus.broadcast_to_one(process_cmd)
        current_tracking_id = process_cmd.id
        
        print("Waiting for LLM reply...")
        import time
        while self.active:
            result_item = self.bus.get_result(current_tracking_id)
            if result_item is not None:
                print("\n[LLM_AGENT]: " + str(result_item.get("result", "")))
                reply = input("[YOU] (type 'exit' to leave auto mode)> ").strip()
                if reply.lower() == 'exit':
                    print("--- Exiting Auto Mode ---")
                    break
                else:
                    new_cmd = AgentCommandFactory.process_user_prompt({"prompt": reply})
                    self.bus.broadcast_to_one(new_cmd)
                    current_tracking_id = new_cmd.id
                    print("Waiting for LLM reply...")
            else:
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    print("\n--- Exiting Auto Mode ---")
                    break
                    
        self.bus.write_result(claimed_cmd.id, claimed_cmd.command_name, {"status": "exited"}, self.__class__.__name__)
