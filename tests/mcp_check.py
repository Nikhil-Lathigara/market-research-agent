import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import StdioServerParameters
from crewai_tools import MCPServerAdapter

load_dotenv()

project_dir = Path(__file__).resolve().parent.parent
server_file = project_dir / "mcp_server.py"

print("1. Python executable:", sys.executable)
print("2. MCP server path:", server_file)
print("3. Server file exists:", server_file.exists())

if not server_file.exists():
    raise FileNotFoundError(f"MCP server not found: {server_file}")

server_params = StdioServerParameters(
    command=sys.executable,
    args=[str(server_file)],
    env=os.environ.copy(),
)

print("\n4. Connecting to MCP server...")

with MCPServerAdapter(server_params, connect_timeout=30) as tools:
    print("\n5. MCP connection successful!")
    print("6. Number of tools discovered:", len(tools))

    for tool in tools:
        print(f"- {tool.name}")

print("\n7. MCP connection closed.")
