"""Real stdio smoke test using both installed client configurations (no LLM call)."""
import argparse
import json
from pathlib import Path
import queue
import subprocess
import threading
import time
import tomllib

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "rackclick-desarrollo"
READ_TOOLS = {"search_graph", "query_graph", "trace_path", "get_code_snippet", "get_file_outline",
              "get_graph_schema", "compare_graphs", "get_architecture", "search_code", "list_projects",
              "index_status", "check_index_coverage", "detect_changes"}


class Session:
    def __init__(self, configuration):
        self.queue = queue.Queue()
        self.serial = 0
        self.process = subprocess.Popen([configuration["command"], *configuration["args"]],
                                        cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        def read():
            for line in self.process.stdout:
                try:
                    self.queue.put(json.loads(line))
                except ValueError:
                    self.queue.put({"protocol_error": True})
            self.queue.put({"eof": True})
        threading.Thread(target=read, daemon=True).start()

    def request(self, method, params=None):
        self.serial += 1
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.serial, "method": method,
                                            "params": params or {}}) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + 120
        while True:
            value = self.queue.get(timeout=max(0.1, deadline - time.monotonic()))
            if value.get("protocol_error") or value.get("eof"):
                raise AssertionError("Invalid MCP protocol / premature exit")
            if value.get("id") == self.serial:
                if "error" in value:
                    raise AssertionError(value["error"])
                return value["result"]

    def call(self, name, arguments=None):
        result = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        if result.get("isError"):
            raise AssertionError("Tool failed: " + name)
        return result

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    codex = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8-sig"))["mcp_servers"]["rackclick_codebase"]
    settings = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8-sig"))
    entries = [v for k, v in settings.get("projects", {}).items() if Path(k).resolve() == ROOT.resolve()]
    claude = entries[0]["mcpServers"]["rackclick_codebase"]
    assert (codex["command"], codex["args"]) == (claude["command"], claude["args"])
    sessions = []
    observations = {}
    try:
        # Keep both sessions open: they must observe the same project/cache simultaneously.
        for label, config in [("Codex", codex), ("Claude", claude)]:
            start = time.monotonic()
            session = Session(config)
            sessions.append(session)
            init = session.request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                                  "clientInfo": {"name": "rackclick-smoke-" + label.lower(), "version": "1"}})
            session.process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
            session.process.stdin.flush()
            tools = {t["name"] for t in session.request("tools/list")["tools"]}
            assert tools == READ_TOOLS, tools
            projects = session.call("list_projects")
            assert PROJECT in json.dumps(projects) and "total: 1" in json.dumps(projects)
            status = session.call("index_status", {"project": PROJECT})
            assert "status: ready" in json.dumps(status)
            symbol = session.call("search_graph", {"project": PROJECT, "name_pattern": "^MfaStore$", "limit": 3})
            assert "development/server/src/RackClick.Server/MfaStore.cs" in json.dumps(symbol)
            frontend = session.call("search_graph", {"project": PROJECT, "name_pattern": "^InventoryPanel$", "limit": 3})
            assert "development/frontend/src/InventoryPanel.jsx" in json.dumps(frontend)
            route = session.call("search_code", {"project": PROJECT, "pattern": "recover-admin", "file_pattern": "*.ps1", "limit": 2})
            assert "tools/windows/New-RackClickRecoveredInstance.ps1" in json.dumps(route)
            # An excluded root cannot be discovered through the source-search surface.
            excluded = session.call("search_code", {"project": PROJECT, "pattern": "CBM_PRIVATE_SENTINEL_25OCT", "path_filter": ".local/", "limit": 1})
            assert "CBM_PRIVATE_SENTINEL_25OCT" not in json.dumps(excluded)
            observations[label] = {"initialize": init, "tools": sorted(tools), "projects": projects,
                                   "status": status, "symbol": symbol, "frontend": frontend, "recovery": route,
                                   "excludedSearch": excluded, "seconds": round(time.monotonic() - start, 3)}
        assert observations["Codex"]["status"] == observations["Claude"]["status"]
    finally:
        for session in reversed(sessions):
            session.close()
    result = {"success": True, "method": "real stdio from both client configuration commands; no model invocation",
              "sameIndex": True, "clients": observations}
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"success": True, "sameIndex": True, "readOnlyTools": len(READ_TOOLS),
                      "seconds": {k: v["seconds"] for k, v in observations.items()}}))


if __name__ == "__main__":
    main()
