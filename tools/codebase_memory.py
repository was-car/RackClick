"""Local RackClick source map. No product deployment or access to lab data.

Usage: python -B tools/codebase_memory.py refresh|serve|status|scope|view|close-view
The native executable is installed separately, pinned to VERSION and SHA256.
Only allowlisted source files reach the private, generated mirror and index.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import urllib.request
import webbrowser

VERSION = "0.12.1"
ARCHIVE_SHA256 = "4e4e0f16b45233af5c757a1fcbe3c3b16e9056375b1fbe2ce020b6de75dedcc0"
PROJECT = "rackclick-desarrollo"
REPOSITORY = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "RackClick/CodebaseMemory"
MIRROR = BASE / "source"
BINARY = BASE / "bin" / ("v" + VERSION) / "codebase-memory-mcp.exe"
SOURCE_DIRS = (
    "development/server/src", "development/server/database", "development/server/tests",
    "development/frontend/src", "development/frontend/tests", "development/windows-service",
    "tools/windows", "tools/tests", "tools/catalog", "development/catalog",
)
DOCS = (
    "AGENTS.md", "README.md", "docs/BRIEFING-MAESTRO.md", "docs/CONTINUIDAD-CODEX.md",
    "docs/INICIO-IMPLEMENTACION-S1.md", "docs/CONTRATO-SERVIDOR-v0.1.md",
    "docs/MAPA-RC9-R3.md", "docs/ACEPTACION.md", "docs/S1-FUNDAMENTO.md",
    "docs/METODOLOGIA-PARA-CLAUDE.md", "docs/IMPLEMENTACION-REV4.md",
    "docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md", "docs/PLAN-CIERRE-RACKCLICK.md",
    "docs/PROGRESO-GLOBAL.md", "docs/CANDIDATA-INSTALADOR08-25-10-2026.md",
    "docs/MENSAJE-PARA-CLAUDE-CODEBASE-MEMORY-25-10-2026.md",
    "development/server/README.md", "development/server/global.json",
    "development/frontend/package.json", "development/frontend/vite.config.js",
)
EXTENSIONS = {".cs", ".csproj", ".props", ".targets", ".sln", ".slnx", ".sql", ".ts", ".tsx",
              ".js", ".jsx", ".mjs", ".py", ".ps1", ".psm1", ".psd1", ".css"}
SKIP_DIRS = {".git", ".local", ".artifacts", "node_modules", "bin", "obj", "dist", "__pycache__",
             ".venv", "rc9-reference", "backups", "backup", "private", "secrets", "credentials"}
MAX_FILE_BYTES = 2 * 1024 * 1024
VIEW_URL = "http://127.0.0.1:9749/?project=" + PROJECT + "&workspace=architecture"
VIEW_HEALTH = "http://127.0.0.1:9749/api/project-health?name=" + PROJECT


def walk_error(error: OSError) -> None:
    raise error


def no_reparse(path: Path) -> None:
    """Check the path and every ancestor without following Windows junctions."""
    for component in (path, *path.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Reparse path refused: " + str(component))


def selected_files(root: Path = REPOSITORY) -> list[Path]:
    result: set[Path] = set()
    no_reparse(root)
    for relative in SOURCE_DIRS:
        start = root / relative
        if not start.exists():
            continue
        no_reparse(start)
        for directory, directories, files in os.walk(start, followlinks=False, onerror=walk_error):
            parent = Path(directory)
            directories[:] = [n for n in directories if n.lower() not in SKIP_DIRS]
            for name in directories:
                no_reparse(parent / name)
            for name in files:
                path = parent / name
                if path.suffix.lower() in EXTENSIONS:
                    no_reparse(path)
                    result.add(path)
    # Only immediate source scripts in tools; no traversal of other root folders.
    if (root / "tools").is_dir():
        for path in (root / "tools").iterdir():
            if path.suffix.lower() in EXTENSIONS:
                no_reparse(path)
                if path.is_file():
                    result.add(path)
    for relative in DOCS:
        path = root / relative
        if path.exists():
            no_reparse(path)
            if path.is_file():
                result.add(path)
    return sorted(result, key=lambda p: p.relative_to(root).as_posix())


def environment() -> dict[str, str]:
    env = os.environ.copy()
    env.update(CBM_CACHE_DIR=str(BASE / "cache"), CBM_RUNTIME_DIR=str(BASE / "runtime"),
               CBM_ALLOWED_ROOT=str(MIRROR))
    return env


def support_paths() -> None:
    for path in (BASE, MIRROR, BINARY, BASE / "cache", BASE / "runtime", BASE / "refresh.lock",
                 BASE / "source-state.json", BASE / "last-index.json", BASE / "last-index-stderr.log",
                 BASE / "viewer.lock", BASE / "viewer.log", BASE / "viewer-close.request"):
        no_reparse(path)


@contextlib.contextmanager
def sync_lock():
    import msvcrt
    support_paths()
    BASE.mkdir(parents=True, exist_ok=True)
    with (BASE / "refresh.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        deadline = time.monotonic() + 120
        while True:
            try:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Another map refresh is still running")
                time.sleep(0.25)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def cli(tool: str, arguments: dict | None = None) -> subprocess.CompletedProcess:
    support_paths()
    return subprocess.run([str(BINARY), "cli", "--json", tool],
                          input=json.dumps(arguments or {}), capture_output=True, text=True,
                          encoding="utf-8", cwd=MIRROR, env=environment(), timeout=300)


def index_ready() -> bool:
    outcome = cli("index_status", {"project": PROJECT})
    try:
        envelope = json.loads(outcome.stdout)
        fields = {}
        for block in envelope.get("content", []):
            if block.get("type") == "text":
                for line in block.get("text", "").splitlines():
                    if line and not line[0].isspace() and ": " in line:
                        key, value = line.split(": ", 1)
                        fields[key] = value
        return (outcome.returncode == 0 and not envelope.get("isError")
                and fields.get("status") == "ready" and fields.get("project") == PROJECT
                and Path(fields.get("root_path", "")).resolve() == MIRROR.resolve())
    except (ValueError, TypeError, AttributeError):
        return False


def refresh() -> dict:
    with sync_lock():
        no_reparse(BINARY)
        if not BINARY.is_file():
            raise FileNotFoundError("Install official CBM " + VERSION + " first: " + str(BINARY))
        no_reparse(MIRROR)
        MIRROR.mkdir(parents=True, exist_ok=True)
        inventory = []
        mirror_changed = False
        # Read only selected sources, never inspect excluded folders or their contents.
        for source in selected_files():
            if source.stat().st_size > MAX_FILE_BYTES:
                raise ValueError("Source exceeds size limit: " + str(source.relative_to(REPOSITORY)))
            data = source.read_bytes()
            relative = source.relative_to(REPOSITORY)
            target = MIRROR / relative
            no_reparse(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(data).hexdigest()
            if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                temporary = target.with_name(target.name + ".cbm-tmp")
                no_reparse(temporary)
                temporary.write_bytes(data)
                temporary.replace(target)
                mirror_changed = True
            inventory.append({"path": relative.as_posix(), "sha256": digest, "bytes": len(data)})
        allowed = {item["path"] for item in inventory} | {".codebase-memory.json", ".cbmignore"}
        # Delete only generated mirror files that were removed from the allowlist/sources.
        for directory, directories, files in os.walk(MIRROR, followlinks=False, onerror=walk_error):
            parent = Path(directory)
            for name in directories:
                no_reparse(parent / name)
            for name in files:
                path = parent / name
                no_reparse(path)
                if path.relative_to(MIRROR).as_posix() not in allowed:
                    if not path.resolve().is_relative_to(MIRROR.resolve()):
                        raise ValueError("Generated-file cleanup escaped mirror")
                    path.unlink()
                    mirror_changed = True
        no_reparse(MIRROR / ".codebase-memory.json")
        no_reparse(MIRROR / ".cbmignore")
        (MIRROR / ".codebase-memory.json").write_text(
            '{"extra_extensions":{".mjs":"javascript"}}\n', encoding="utf-8")
        (MIRROR / ".cbmignore").write_text(
            ".local/\n.git/\nnode_modules/\n**/bin/\n**/obj/\n*.pfx\n*.key\n.env*\n", encoding="utf-8")
        fingerprint = hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()
        state_path = BASE / "source-state.json"
        previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        indexed = not mirror_changed and previous.get("fingerprint") == fingerprint and index_ready()
        result = {"project": PROJECT, "files": len(inventory), "fingerprint": fingerprint,
                  "sourceRoot": str(REPOSITORY), "mirrorRoot": str(MIRROR), "reindexed": not indexed}
        if not indexed:
            outcome = cli("index_repository", {"repo_path": str(MIRROR), "name": PROJECT, "mode": "full"})
            (BASE / "last-index.json").write_text(outcome.stdout, encoding="utf-8")
            (BASE / "last-index-stderr.log").write_text(outcome.stderr, encoding="utf-8")
            try:
                envelope = json.loads(outcome.stdout)
            except ValueError:
                envelope = {"isError": True}
            content = envelope.get("structuredContent", {})
            if (outcome.returncode or envelope.get("isError") or content.get("status") != "indexed"
                    or content.get("project") != PROJECT or not index_ready()):
                raise RuntimeError("CBM index failed; see private last-index logs")
            # Never mark a failed or asynchronous job as a completed snapshot.
            state_path.write_text(json.dumps({**result, "inventory": inventory}, indent=2), encoding="utf-8")
        return result


def viewer_ready() -> bool:
    try:
        # Never send this source-map check through a system HTTP proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(VIEW_HEALTH, timeout=2) as response:
            result = json.load(response)
        return result.get("status") == "healthy"
    except (OSError, ValueError):
        return False


def viewer_host() -> int:
    """Keep one native UI session alive, hidden, at most eight hours. No service/task."""
    import msvcrt
    support_paths()
    with (BASE / "viewer.lock").open("a+b") as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return 0  # A prior launcher already owns the viewer session.
        stop = BASE / "viewer-close.request"
        if stop.exists():
            stop.unlink()
        try:
            with (BASE / "viewer.log").open("a", encoding="utf-8") as log:
                # This local UI controller is separate from the agents' analysis profile.
                native = subprocess.Popen([str(BINARY), "--ui=true", "--port=9749"], cwd=MIRROR,
                                          env=environment(), stdin=subprocess.PIPE,
                                          stdout=subprocess.DEVNULL, stderr=log,
                                          creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    deadline = time.monotonic() + 8 * 60 * 60
                    while native.poll() is None and time.monotonic() < deadline:
                        no_reparse(stop)
                        if stop.exists():
                            break
                        time.sleep(1)
                finally:
                    native.stdin.close()
                    try:
                        native.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        native.terminate()  # Only this child, never the shared daemon or agents.
                        native.wait(timeout=10)
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    return 0


def open_viewer(open_browser: bool = True) -> dict:
    result = refresh()
    if not viewer_ready():
        support_paths()
        def launch():
            return subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "view-host"],
                                    cwd=REPOSITORY, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        controller = launch()
        last_launch = time.monotonic()
        deadline = time.monotonic() + 25
        while not viewer_ready():
            if time.monotonic() >= deadline:
                raise RuntimeError("No se pudo abrir el mapa; consulte el log privado viewer.log")
            # A previous close may still hold the viewer lock briefly. Retry after it exits.
            if controller.poll() is not None and time.monotonic() - last_launch >= 2:
                controller = launch()
                last_launch = time.monotonic()
            time.sleep(0.3)
    if open_browser:
        if not webbrowser.open(VIEW_URL, new=2):
            raise RuntimeError("El mapa esta disponible; abra esta direccion en su navegador: " + VIEW_URL)
    return {**result, "url": VIEW_URL, "viewerHealthy": True}


def close_viewer() -> None:
    support_paths()
    (BASE / "viewer-close.request").write_text("close\n", encoding="ascii")
    # Reconfigure only the UI; analysis sessions and their shared daemon keep running.
    with (BASE / "viewer.log").open("a", encoding="utf-8") as log:
        native = subprocess.Popen([str(BINARY), "--ui=false"], cwd=MIRROR, env=environment(),
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=log,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        native.wait(timeout=20)
        if native.returncode:
            raise RuntimeError("No se pudo cerrar el visor local")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("refresh", "serve", "status", "scope", "view", "view-host", "close-view"))
    args = parser.parse_args()
    if args.action == "view-host":
        return viewer_host()
    if args.action == "view":
        print("Actualizando el mapa de RackClick y abriendo Architecture...")
        print(json.dumps(open_viewer()))
    elif args.action == "close-view":
        close_viewer()
        print("Visor cerrado; conexiones MCP de los agentes conservadas.")
    elif args.action == "scope":
        print(json.dumps([p.relative_to(REPOSITORY).as_posix() for p in selected_files()], indent=2))
    elif args.action == "status":
        result = cli("index_status", {"project": PROJECT})
        print(result.stdout)
        return result.returncode
    else:
        result = refresh()
        if args.action == "refresh":
            print(json.dumps(result))
        else:
            print("RackClick source map: " + json.dumps(result), file=sys.stderr)
            support_paths()
            return subprocess.call([str(BINARY), "--tool-profile=analysis", "--ui=false"],
                                   cwd=MIRROR, env=environment())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as error:
        print("RackClick Codebase Memory: " + str(error), file=sys.stderr)
        raise SystemExit(1)
