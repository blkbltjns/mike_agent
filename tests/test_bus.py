from bus import Bus, Inbox, Outbox
from agent_command import AgentCommand

class TestBus:
    def test_bus_initializes_queues(self):
        bus = Bus()
        assert isinstance(bus._inbox, Inbox)
        assert isinstance(bus._outbox, Outbox)
        
    def test_enqueue_and_claim_flow(self):
        bus = Bus()
        cmd = AgentCommand("dummy_command")
        
        req = bus.enqueue(cmd)
        assert req.command_name == "dummy_command"
        
        claimed = bus.claim(["dummy_command"])
        assert claimed is not None
        assert claimed.id == cmd.id
        
    def test_write_and_get_result(self):
        bus = Bus()
        bus.write_result("req-123", "dummy_command", "Result")
        
        result = bus.get_result("req-123")
        assert result is not None
        assert result["result"] == "Result"
        assert result["command_name"] == "dummy_command"

    def test_get_result_none_for_missing_id(self):
        bus = Bus()
        bus.write_result("req-123", "dummy_command", "Result")
        assert bus.get_result("nonexistent") is None


class TestInbox:
    def test_inbox_behavior(self):
        inbox = Inbox()
        cmd = inbox.enqueue(AgentCommand("dummy_command"))
        assert not inbox.is_empty()
        claimed_cmd = inbox.claim(["dummy_command"])
        assert claimed_cmd is cmd
        assert claimed_cmd.is_claimed
        assert not inbox.is_empty()  # Queue never pops
        assert inbox.claim(["dummy_command"]) is None # Already claimed

    def test_inbox_unique_ids(self):
        inbox = Inbox()
        r1 = inbox.enqueue(AgentCommand("dummy_command"))
        r2 = inbox.enqueue(AgentCommand("dummy_command"))
        assert r1.id != r2.id


class TestOutbox:
    def test_outbox_behavior(self):
        outbox = Outbox()
        outbox.append("req-123", "dummy_command", "Result", "Agent1")
        assert len(outbox) == 1
        entry = outbox.items()[0]
        assert entry["request_id"] == "req-123"
        assert entry["result"] == "Result"
        assert entry["agent_name"] == "Agent1"
