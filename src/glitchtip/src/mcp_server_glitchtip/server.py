import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse

import click
import httpx
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import McpError
import mcp.server.stdio
import os

GLITCHTIP_API_BASE = os.getenv("GLITCHTIP_API_URL", "https://app.glitchtip.com/api/0/")
MISSING_AUTH_TOKEN_MESSAGE = (
    """GlitchTip authentication token not found. Please specify your GlitchTip auth token."""
)


@dataclass
class GlitchTipIssueData:
    title: str
    issue_id: str
    status: str
    level: str
    first_seen: str
    last_seen: str
    count: int
    stacktrace: str

    def to_text(self) -> str:
        return f"""
GlitchTip Issue: {self.title}
Issue ID: {self.issue_id}
Status: {self.status}
Level: {self.level}
First Seen: {self.first_seen}
Last Seen: {self.last_seen}
Event Count: {self.count}

{self.stacktrace}
        """

    def to_prompt_result(self) -> types.GetPromptResult:
        return types.GetPromptResult(
            description=f"GlitchTip Issue: {self.title}",
            messages=[
                types.PromptMessage(
                    role="user", content=types.TextContent(type="text", text=self.to_text())
                )
            ],
        )

    def to_tool_result(self) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        return [types.TextContent(type="text", text=self.to_text())]


class GlitchTipError(Exception):
    pass


def extract_issue_id(issue_id_or_url: str) -> str:
    """
    Extracts the GlitchTip issue ID from either a full URL or a standalone ID.

    This function validates the input and returns the numeric issue ID.
    It raises GlitchTipError for invalid inputs, including empty strings,
    non-GlitchTip URLs, malformed paths, and non-numeric IDs.
    """
    if not issue_id_or_url:
        raise GlitchTipError("Missing issue_id_or_url argument")

    if issue_id_or_url.startswith(("http://", "https://")):
        parsed_url = urlparse(issue_id_or_url)
        if not parsed_url.hostname:
            raise GlitchTipError("Invalid GlitchTip URL")

        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) < 3 or path_parts[1] != "issues":
            raise GlitchTipError(
                "Invalid GlitchTip issue URL. Path must contain '/issues/{issue_id}'"
            )

        issue_id = path_parts[-1]
    else:
        issue_id = issue_id_or_url

    if not issue_id.isdigit():
        raise GlitchTipError("Invalid GlitchTip issue ID. Must be a numeric value.")

    return issue_id


def create_stacktrace(latest_event: dict) -> str:
    """
    Creates a formatted stacktrace string from the latest GlitchTip event.

    This function extracts exception information and stacktrace details from the
    provided event dictionary, formatting them into a human-readable string.
    It handles multiple exceptions and includes file, line number, and function
    information for each frame in the stacktrace.

    Args:
        latest_event (dict): A dictionary containing the latest GlitchTip event data.

    Returns:
        str: A formatted string containing the stacktrace information,
             or "No stacktrace found" if no relevant data is present.
    """
    stacktraces = []
    for entry in latest_event.get("entries", []):
        if entry["type"] != "exception":
            continue

        exception_data = entry["data"]["values"]
        for exception in exception_data:
            exception_type = exception.get("type", "Unknown")
            exception_value = exception.get("value", "")
            stacktrace = exception.get("stacktrace")

            stacktrace_text = f"Exception: {exception_type}: {exception_value}\n\n"
            if stacktrace:
                stacktrace_text += "Stacktrace:\n"
                for frame in stacktrace.get("frames", []):
                    filename = frame.get("filename", "Unknown")
                    lineno = frame.get("lineNo", "?")
                    function = frame.get("function", "Unknown")

                    stacktrace_text += f"{filename}:{lineno} in {function}\n"

                    if "context" in frame:
                        context = frame["context"]
                        for ctx_line in context:
                            stacktrace_text += f"    {ctx_line[1]}\n"

                    stacktrace_text += "\n"

            stacktraces.append(stacktrace_text)

    return "\n".join(stacktraces) if stacktraces else "No stacktrace found"


async def handle_glitchtip_issue(
    http_client: httpx.AsyncClient, auth_token: str, issue_id_or_url: str
) -> GlitchTipIssueData:
    try:
        issue_id = extract_issue_id(issue_id_or_url)

        response = await http_client.get(
            f"issues/{issue_id}/", headers={"Authorization": f"Bearer {auth_token}"}
        )
        if response.status_code == 401:
            raise McpError(
                "Error: Unauthorized. Please check your MCP_GLITCHTIP_AUTH_TOKEN token."
            )
        response.raise_for_status()
        issue_data = response.json()

        # Get issue latest event
        latest_event_response = await http_client.get(
            f"issues/{issue_id}/events/latest/",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        latest_event_response.raise_for_status()
        latest_event = latest_event_response.json()
        stacktrace = create_stacktrace(latest_event)

        return GlitchTipIssueData(
            title=issue_data["title"],
            issue_id=issue_id,
            status=issue_data["status"],
            level=issue_data["level"],
            first_seen=issue_data["firstSeen"],
            last_seen=issue_data["lastSeen"],
            count=issue_data["count"],
            stacktrace=stacktrace
        )

    except GlitchTipError as e:
        raise McpError(str(e))
    except httpx.HTTPStatusError as e:
        raise McpError(f"Error fetching GlitchTip issue: {str(e)}")
    except Exception as e:
        raise McpError(f"An error occurred: {str(e)}")


async def serve(auth_token: str) -> Server:
    server = Server("glitchtip")
    http_client = httpx.AsyncClient(base_url=GLITCHTIP_API_BASE)

    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        return [
            types.Prompt(
                name="glitchtip-issue",
                description="Retrieve a GlitchTip issue by ID or URL",
                arguments=[
                    types.PromptArgument(
                        name="issue_id_or_url",
                        description="GlitchTip issue ID or URL",
                        required=True,
                    )
                ],
            )
        ]

    @server.get_prompt()
    async def handle_get_prompt(
        name: str, arguments: dict[str, str] | None
    ) -> types.GetPromptResult:
        if name != "glitchtip-issue":
            raise ValueError(f"Unknown prompt: {name}")

        issue_id_or_url = (arguments or {}).get("issue_id_or_url", "")
        issue_data = await handle_glitchtip_issue(http_client, auth_token, issue_id_or_url)
        return issue_data.to_prompt_result()

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="get_glitchtip_issue",
                description="""Retrieve and analyze a GlitchTip issue by ID or URL. Use this tool when you need to:
                - Investigate production errors and crashes
                - Access detailed stacktraces from GlitchTip
                - Analyze error patterns and frequencies
                - Get information about when issues first/last occurred
                - Review error counts and status""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_id_or_url": {
                            "type": "string",
                            "description": "GlitchTip issue ID or URL to analyze"
                        }
                    },
                    "required": ["issue_id_or_url"]
                }
            )
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if name != "get_glitchtip_issue":
            raise ValueError(f"Unknown tool: {name}")

        if not arguments or "issue_id_or_url" not in arguments:
            raise ValueError("Missing issue_id_or_url argument")

        try:
            issue_data = await handle_glitchtip_issue(http_client, auth_token, arguments["issue_id_or_url"])
            return issue_data.to_tool_result()
        except Exception as e:
            error_message = str(e)
            return [types.TextContent(type="text", text=error_message)]

    return server

@click.command()
@click.option(
    "--auth-token",
    envvar="GLITCHTIP_TOKEN",
    required=True,
    help="GlitchTip authentication token",
)
def main(auth_token: str):
    async def _run():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            server = await serve(auth_token)
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="glitchtip",
                    server_version="0.4.1",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    asyncio.run(_run())
