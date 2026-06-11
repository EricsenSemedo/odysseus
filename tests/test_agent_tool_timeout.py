"""Regression guards for foreground agent subprocess timeouts."""

import asyncio

from src.agent_tools import ToolBlock
from src import tool_execution


def test_foreground_bash_tool_times_out_promptly(monkeypatch):
    """A hung foreground shell command should not pin the chat for an hour."""
    monkeypatch.setattr(tool_execution, "DEFAULT_BASH_TIMEOUT", 0.1)
    monkeypatch.setattr(tool_execution, "is_public_blocked_tool", lambda _tool: False)

    async def _run():
        return await tool_execution.execute_tool_block(
            ToolBlock("bash", "sleep 5"),
            owner="admin",
        )

    _desc, result = asyncio.run(_run())

    assert result["exit_code"] == 124
    assert "timed out after 0.1s" in result["error"]


def test_documented_foreground_tool_timeouts_match_prompt():
    assert tool_execution.DEFAULT_BASH_TIMEOUT == 60
    assert tool_execution.DEFAULT_PYTHON_TIMEOUT == 60
