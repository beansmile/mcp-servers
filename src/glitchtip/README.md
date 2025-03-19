# mcp-server-glitchtip: A Glitchtip MCP server

## Overview

A Model Context Protocol server for retrieving and analyzing issues from Glitchtip. This server provides tools to inspect error reports, stacktraces, and other debugging information from your Glitchtip account.

### Tools

1. `get_glitchtip_issue`
   - Retrieve and analyze a Glitchtip issue by ID or URL
   - Input:
     - `issue_id_or_url` (string): Glitchtip issue ID or URL to analyze
   - Returns: Issue details including:
     - Title
     - Issue ID
     - Status
     - Level
     - First seen timestamp
     - Last seen timestamp
     - Event count
     - Full stacktrace

### Prompts

1. `glitchtip-issue`
   - Retrieve issue details from Glitchtip
   - Input:
     - `issue_id_or_url` (string): Glitchtip issue ID or URL
   - Returns: Formatted issue details as conversation context

## Installation

### Using uv (recommended)

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run *mcp-server-glitchtip*.

### Using PIP

Alternatively you can install `mcp-server-glitchtip` via pip:

```
pip install mcp-server-glitchtip
```

After installation, you can run it as a script using:

```
python -m mcp_server_glitchtip
```

## Configuration

### Usage with Claude Desktop

Add this to your `claude_desktop_config.json`:

<details>
<summary>Using uvx</summary>

```json
"mcpServers": {
  "glitchtip": {
    "command": "uvx",
    "args": ["mcp-server-glitchtip", "--auth-token", "YOUR_GLITCHTIP_TOKEN"]
  }
}
```
</details>

<details>

<details>
<summary>Using docker</summary>

```json
"mcpServers": {
  "glitchtip": {
    "command": "docker",
    "args": ["run", "-i", "--rm", "mcp/glitchtip", "--auth-token", "YOUR_GLITCHTIP_TOKEN"]
  }
}
```
</details>

<details>

<summary>Using pip installation</summary>

```json
"mcpServers": {
  "glitchtip": {
    "command": "python",
    "args": ["-m", "mcp_server_glitchtip", "--auth-token", "YOUR_GLITCHTIP_TOKEN"]
  }
}
```
</details>

### Usage with [Zed](https://github.com/zed-industries/zed)

Add to your Zed settings.json:

<details>
<summary>Using uvx</summary>

```json
"context_servers": [
  "mcp-server-glitchtip": {
    "command": {
      "path": "uvx",
      "args": ["mcp-server-glitchtip", "--auth-token", "YOUR_GLITCHTIP_TOKEN"]
    }
  }
],
```
</details>

<details>
<summary>Using pip installation</summary>

```json
"context_servers": {
  "mcp-server-glitchtip": {
    "command": "python",
    "args": ["-m", "mcp_server_glitchtip", "--auth-token", "YOUR_GLITCHTIP_TOKEN"]
  }
},
```
</details>

## Debugging

You can use the MCP inspector to debug the server. For uvx installations:

```
npx @modelcontextprotocol/inspector uvx mcp-server-glitchtip --auth-token YOUR_GLITCHTIP_TOKEN
```

Or if you've installed the package in a specific directory or are developing on it:

```
cd path/to/servers/src/glitchtip
npx @modelcontextprotocol/inspector uv run mcp-server-glitchtip --auth-token YOUR_GLITCHTIP_TOKEN
```

## License

This MCP server is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.
