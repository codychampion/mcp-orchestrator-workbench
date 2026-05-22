import asyncio
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

from utils import mcp_utils


class FakeTextContent:
    def __init__(self, text):
        self.text = text


class FakeResult:
    def __init__(self, content):
        self.content = content


class TestExtractToolResult(unittest.TestCase):
    def test_extracts_text_from_first_content_item(self):
        result = FakeResult([FakeTextContent("hello from tool")])
        self.assertEqual(mcp_utils.extract_tool_result(result), "hello from tool")

    def test_falls_back_to_string_when_content_missing(self):
        class PlainResult:
            def __str__(self):
                return "plain-result"

        self.assertEqual(mcp_utils.extract_tool_result(PlainResult()), "plain-result")


class TestCallToolWithRetry(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_client = mcp_utils.Client

    async def asyncTearDown(self):
        mcp_utils.Client = self.original_client

    async def test_retries_once_then_succeeds(self):
        attempts = {"count": 0}

        class FakeClient:
            def __init__(self, mcp_url):
                self.mcp_url = mcp_url

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def call_tool(self, tool_name, params):
                attempts["count"] += 1
                if attempts["count"] == 1:
                    raise RuntimeError("temporary failure")
                return FakeResult([FakeTextContent(f"{tool_name}:{params['value']}")])

        mcp_utils.Client = FakeClient

        result = await mcp_utils.call_tool_with_retry(
            "mock://mcp",
            "echo",
            {"value": "ok"},
            max_retries=1,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["output"], "echo:ok")
        self.assertEqual(result["attempts"], 2)

    async def test_returns_timeout_error(self):
        class SlowClient:
            def __init__(self, mcp_url):
                self.mcp_url = mcp_url

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def call_tool(self, tool_name, params):
                await asyncio.sleep(0.05)
                return FakeResult([FakeTextContent("too late")])

        mcp_utils.Client = SlowClient

        result = await mcp_utils.call_tool_with_retry(
            "mock://mcp",
            "slow_tool",
            {},
            timeout=0.01,
            max_retries=0,
        )

        self.assertFalse(result["success"])
        self.assertIn("timed out", result["error"])
        self.assertEqual(result["attempts"], 1)
