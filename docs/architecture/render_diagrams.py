"""Renders every diagrams/*.mmd to SVG through the Mermaid MCP server (local rendering only)."""

import json
import subprocess
import sys
from pathlib import Path

DIAGRAMS = Path(__file__).resolve().parent / "diagrams"
SERVER = ["npx", "-y", "mcp-mermaid@0.4.1"]


class McpClient:
    """Minimal JSON-RPC client for an MCP server over stdio."""

    def __init__(self, command):
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True)
        self.next_id = 0

    def send(self, method, params=None, notify=False):
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        if not notify:
            self.next_id += 1
            message["id"] = self.next_id
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        if notify:
            return None
        while True:
            reply = json.loads(self.process.stdout.readline())
            if reply.get("id") == self.next_id:
                if "error" in reply:
                    raise RuntimeError(reply["error"])
                return reply["result"]

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=30)


def main():
    client = McpClient(SERVER)
    client.send("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "render-diagrams", "version": "1.0"}})
    client.send("notifications/initialized", notify=True)
    tools = [tool["name"] for tool in client.send("tools/list")["tools"]]
    print("tools:", ", ".join(tools))
    failures = 0
    for source in sorted(DIAGRAMS.glob("*.mmd")):
        result = client.send("tools/call", {"name": "generate_mermaid_diagram",
                                            "arguments": {"mermaid": source.read_text(), "outputType": "svg"}})
        text = "".join(part.get("text", "") for part in result.get("content", []))
        if result.get("isError") or "<svg" not in text:
            failures += 1
            print(f"FAIL {source.name}: {text[:200]}")
            continue
        target = source.with_suffix(".svg")
        target.write_text(text[text.index("<svg"):])
        print(f"ok   {source.name} -> {target.name} ({len(text):,} chars)")
    client.close()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
