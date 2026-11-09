"""Assertions shared by MCP contract tests."""

from typing import Any

from fastmcp import Client
from jsonschema import Draft202012Validator


async def assert_output_matches_schema(
    client: Client[Any], tool_name: str, payload: dict[str, Any] | None
) -> None:
    tool = next(tool for tool in await client.list_tools() if tool.name == tool_name)
    assert tool.output_schema is not None
    assert payload is not None
    Draft202012Validator.check_schema(tool.output_schema)
    Draft202012Validator(tool.output_schema).validate(payload)
