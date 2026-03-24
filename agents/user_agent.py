from agent import Agent
from agent_command_factory import AgentCommandFactory
import json

class UserAgent(Agent):
    """
    An agent that processes user-related tasks via an interactive REPL.
    """
    def __init__(self, bus):
        all_cmds = AgentCommandFactory.get_all_commands()
        super().__init__(incoming_commands=["prompt_user"], outgoing_commands=all_cmds, bus=bus)
        self.pending_tasks = {}
        self.task_counter = 1

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
                elif cmd == "exit" or cmd == "quit":
                    self.stop()
                else:
                    print("Unknown command. Try: view_incoming_commands, reply <id> <text>, enqueue <command> <payload_json>, list_commands")
            except (KeyboardInterrupt, EOFError):
                self.stop()
                print("\nExiting UserAgent loop.")

    def _view_incoming(self):
        # Sweeps bus for all incoming commands
        while True:
            command = self.bus.claim(self.incoming_commands)
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
        print("Authorized Outgoing Commands you can explicitly enqueue:")
        for cmd in self.outgoing_commands:
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

        if command_name not in self.outgoing_commands:
            print(f"Not an authorized outgoing command: {command_name}. Allowed: {self.outgoing_commands}")
            return
            
        from agent_command import AgentCommand
        cmd = AgentCommand(command_name, payload)
        self.bus.enqueue(cmd)
        print(f"Enqueued {command_name} with payload {payload}")
