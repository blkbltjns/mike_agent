from bus import Bus, Inbox, Outbox, BroadcastLog
from agent_command import AgentCommand


class TestBus:
    def test_bus_initializes_queues(self):
        """Spec Section 1 - Bus must encapsulate Inbox, Outbox, and BroadcastLog."""
        bus = Bus()
        assert isinstance(bus._inbox, Inbox)
        assert isinstance(bus._outbox, Outbox)
        assert isinstance(bus._broadcast_log, BroadcastLog)

    def test_broadcast_to_one_and_claim_flow(self):
        """Spec Section 1 - broadcast_to_one commands must be claimable by exactly one agent."""
        bus = Bus()
        cmd = AgentCommand("dummy_command")

        req = bus.broadcast_to_one(cmd)
        assert req.command_name == "dummy_command"

        claimed = bus.claim(["dummy_command"], "agent-1")
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

    def test_broadcast_to_one_cannot_double_claim(self):
        """Spec Section 1 - For broadcast_to_one, an already claimed command must return None to subsequent attempts."""
        bus = Bus()
        cmd = AgentCommand("dummy_command")
        bus.broadcast_to_one(cmd)

        bus.claim(["dummy_command"], "agent-1")
        second = bus.claim(["dummy_command"], "agent-2")

        assert second is None

    def test_broadcast_to_all_delivered_to_multiple_agents(self):
        """Spec Section 1 - broadcast_to_all commands must be returned to each distinct agent_id exactly once."""
        bus = Bus()
        cmd = AgentCommand("system_event")
        bus.broadcast_to_all(cmd)

        result1 = bus.claim(["system_event"], "agent-1")
        result2 = bus.claim(["system_event"], "agent-2")

        assert result1 is not None
        assert result2 is not None
        assert result1.id == result2.id  # Same command delivered to both

    def test_broadcast_to_all_not_returned_twice_to_same_agent(self):
        """Spec Section 1 - A broadcast must not be returned to the same agent_id more than once."""
        bus = Bus()
        cmd = AgentCommand("system_event")
        bus.broadcast_to_all(cmd)

        bus.claim(["system_event"], "agent-1")
        second = bus.claim(["system_event"], "agent-1")

        assert second is None


class TestInbox:
    def test_inbox_behavior(self):
        """Spec Section 1 - Inbox is append-only, claim tracks IDs internally, cannot double-claim."""
        inbox = Inbox()
        cmd = inbox.enqueue(AgentCommand("dummy_command"))
        assert not inbox.is_empty()
        claimed_cmd = inbox.claim(["dummy_command"])
        assert claimed_cmd is cmd
        assert not inbox.is_empty()  # Queue never pops
        assert inbox.claim(["dummy_command"]) is None  # Already claimed

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


class TestBroadcastLog:
    def test_broadcast_log_delivered_to_multiple_agents(self):
        """Spec Section 1 - broadcast_to_all commands are stored separately and delivered per agent_id."""
        log = BroadcastLog()
        cmd = AgentCommand("system_event")
        log.append(cmd)

        r1 = log.claim(["system_event"], "agent-1")
        r2 = log.claim(["system_event"], "agent-2")
        assert r1 is not None
        assert r2 is not None
        assert r1.id == r2.id

    def test_broadcast_log_not_delivered_twice_to_same_agent(self):
        """Spec Section 1 - A broadcast will not be returned to the same agent_id more than once."""
        log = BroadcastLog()
        cmd = AgentCommand("system_event")
        log.append(cmd)

        log.claim(["system_event"], "agent-1")
        second = log.claim(["system_event"], "agent-1")
        assert second is None
