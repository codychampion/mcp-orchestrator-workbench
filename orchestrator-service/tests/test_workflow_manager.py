import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "fastmcp" not in sys.modules:
    fastmcp_stub = types.ModuleType("fastmcp")
    fastmcp_stub.Client = object
    sys.modules["fastmcp"] = fastmcp_stub

if "planner" not in sys.modules:
    sys.modules["planner"] = types.ModuleType("planner")

if "planner.llm_client" not in sys.modules:
    llm_client_stub = types.ModuleType("planner.llm_client")
    llm_client_stub.call_llm = lambda *args, **kwargs: "{}"
    sys.modules["planner.llm_client"] = llm_client_stub

from agents.workflow_manager import WorkflowManager


class TestWorkflowManagerSerialization(unittest.TestCase):
    def test_round_trips_workflow_structure(self):
        manager = WorkflowManager("wf-123", "mock://mcp")
        manager.created_at = "2026-05-21T12:00:00"
        manager.description = "demo workflow"
        manager.add_node("n1", "tool", {"tool": "echo", "params": {"text": "hi"}})
        manager.add_node("n2", "agent", {"agent_type": "executor", "goal": "Summarize"})
        manager.add_edge("n1", "n2")

        exported = manager.to_dict()
        restored = WorkflowManager.from_dict(exported, "mock://mcp")

        self.assertEqual(restored.workflow_id, "wf-123")
        self.assertEqual(restored.created_at, "2026-05-21T12:00:00")
        self.assertEqual(restored.description, "demo workflow")
        self.assertEqual(set(restored.nodes.keys()), {"n1", "n2"})
        self.assertEqual(restored.nodes["n1"].config["tool"], "echo")
        self.assertEqual(restored.nodes["n2"].config["agent_type"], "executor")
        self.assertEqual(restored.edges, [("n1", "n2")])
        self.assertEqual(restored.dependencies["n2"], ["n1"])

    def test_summary_includes_node_status_and_edges(self):
        manager = WorkflowManager("wf-summary", "mock://mcp")
        manager.add_node("n1", "tool", {"tool": "echo"})
        manager.add_node("n2", "agent", {"agent_type": "executor"})
        manager.add_edge("n1", "n2")
        manager.nodes["n1"].status = "success"
        manager.nodes["n1"].result = "done"

        summary = manager.get_summary()

        self.assertEqual(summary["workflow_id"], "wf-summary")
        self.assertEqual(summary["nodes"]["n1"]["status"], "success")
        self.assertEqual(summary["nodes"]["n1"]["result"], "done")
        self.assertEqual(summary["edges"], [("n1", "n2")])
