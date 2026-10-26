"""Pinned official Gitleaks; no secret values or Git identities in output.

Exit codes: 0 verified clean, 10 findings, 2 incomplete/unsafe/tool failure.
Install is explicit. Scans never install, rotate or modify source/history.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import uuid
import zipfile

SOURCE = Path(__file__).resolve().parents[2]
LOCK = json.loads((Path(__file__).with_name("gitleaks.lock.json")).read_text("utf-8"))
VERSION = LOCK["version"]
CACHE = SOURCE / ".local" / "security-tools" / "gitleaks" / VERSION
FINDINGS = 10


class ScanError(Exception):
    """Only finite, non-sensitive error codes may be surfaced."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(args: list[str], cwd: Path, data: bytes | None = None) -> subprocess.CompletedProcess:
    # Never stream child logs: even tool failures can contain source or identities.
    env = os.environ.copy()
    for name in ("GITLEAKS_CONFIG", "GITLEAKS_CONFIG_TOML"):
        env.pop(name, None)
    try:
        return subprocess.run(args, cwd=cwd, input=data, capture_output=True,
                              env=env, timeout=1200, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ScanError("child_process_failed") from exc


def git(repo: Path, *args: str) -> bytes:
    result = run(["git", "--literal-pathspecs", "-c", "core.quotePath=false", *args], repo)
    if result.returncode:
        raise ScanError("git_command_failed")
    return result.stdout


def asset() -> dict:
    key = f"{platform.system()}-{platform.machine()}"
    if key not in LOCK["assets"]:
        raise ScanError("unsupported_platform")
    return LOCK["assets"][key]


def download(name: str) -> bytes:
    url = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/{name}"
    try:
        with urllib.request.urlopen(url, timeout=90) as response:
            parsed = urllib.parse.urlsplit(response.url)
            # Official GitHub release assets redirect to GitHub's asset service.
            if parsed.scheme != "https" or parsed.hostname not in {
                "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"
            }:
                raise ScanError("download_origin_invalid")
            return response.read(40 * 1024 * 1024 + 1)
    except (OSError, ValueError) as exc:
        raise ScanError("official_download_failed") from exc


def extract_binary(archive: bytes, name: str) -> bytes:
    # Read a single exact regular member; never extract archive paths.
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            members = [info for info in bundle.infolist() if info.filename == "gitleaks.exe"]
            if len(members) != 1 or members[0].is_dir():
                raise ScanError("archive_binary_invalid")
            return bundle.read(members[0])
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        members = [member for member in bundle if member.name == "gitleaks" and member.isfile()]
        if len(members) != 1:
            raise ScanError("archive_binary_invalid")
        stream = bundle.extractfile(members[0])
        if stream is None:
            raise ScanError("archive_binary_invalid")
        return stream.read()


def executable() -> Path:
    selected = asset()
    archive = CACHE / selected["name"]
    binary = CACHE / ("gitleaks.exe" if platform.system() == "Windows" else "gitleaks")
    if not archive.is_file() or not binary.is_file():
        raise ScanError("gitleaks_missing_run_install")
    payload = archive.read_bytes()
    if digest(payload) != selected["sha256"]:
        raise ScanError("archive_checksum_mismatch")
    if digest(binary.read_bytes()) != digest(extract_binary(payload, selected["name"])):
        raise ScanError("binary_checksum_mismatch")
    version = run([str(binary), "version"], SOURCE)
    if version.returncode or version.stdout.decode("utf-8").strip() != VERSION:
        raise ScanError("binary_version_mismatch")
    return binary


def install() -> dict:
    selected = asset()
    if CACHE.exists():
        binary = executable()  # Never silently overwrite a damaged/foreign install.
        return {"status": "already_verified", "version": VERSION,
                "binarySha256": digest(binary.read_bytes())}
    checksums = download(f"gitleaks_{VERSION}_checksums.txt")
    if digest(checksums) != LOCK["checksumsSha256"]:
        raise ScanError("checksums_manifest_mismatch")
    checksum_lines = [line.split() for line in checksums.decode("ascii").splitlines()]
    expected = [line[0] for line in checksum_lines if len(line) == 2 and line[1] == selected["name"]]
    if expected != [selected["sha256"]]:
        raise ScanError("release_checksum_mismatch")
    payload = download(selected["name"])
    if digest(payload) != selected["sha256"]:
        raise ScanError("archive_checksum_mismatch")
    binary_data = extract_binary(payload, selected["name"])
    CACHE.mkdir(parents=True, exist_ok=False)
    (CACHE / selected["name"]).write_bytes(payload)
    (CACHE / f"gitleaks_{VERSION}_checksums.txt").write_bytes(checksums)
    binary = CACHE / ("gitleaks.exe" if platform.system() == "Windows" else "gitleaks")
    binary.write_bytes(binary_data)
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    executable()
    receipt = {"status": "installed_verified", "version": VERSION,
               "asset": selected["name"], "archiveSha256": selected["sha256"],
               "binarySha256": digest(binary_data), "source": LOCK["releaseUrl"]}
    (CACHE / "installation.json").write_text(json.dumps(receipt, indent=2) + "\n", "utf-8")
    return receipt


def private_path(name: str) -> bool:
    parts = PurePosixPath(name.replace("\\", "/")).parts
    lowered = [part.casefold() for part in parts]
    filename = lowered[-1] if lowered else ""
    return (any(part in {".local", "privados.local", ".localgit", ".git"} for part in lowered)
            or filename.startswith(".env")
            or filename in {"admin-login.json", "appsettings.local.json", "rackclick-backup-all.json"}
            or filename.startswith("resultados-qa-wascar-")
            or filename.endswith((".pfx", ".p12", ".key", ".dump", ".sqlite", ".sqlite3", ".db", ".binlog", ".dmp")))


def names(raw: bytes) -> list[str]:
    return [item.decode("utf-8", errors="strict") for item in raw.split(b"\0") if item]


def validate_names(paths: list[str]) -> None:
    for name in paths:
        path = PurePosixPath(name)
        windows = PureWindowsPath(name)
        if (path.is_absolute() or windows.drive or windows.root or "\\" in name
                or ":" in name or ".." in path.parts or private_path(name)):
            raise ScanError("private_or_unsafe_tracked_path")


def validate_history_metadata(repo: Path) -> int:
    # --raw/--no-renames loads tree metadata only, never patch/blob contents.
    records = git(repo, "log", "--all", "--full-history", "-m", "--root", "--format=",
                  "--raw", "-z", "--no-abbrev", "--no-renames").split(b"\0")
    count = position = 0
    while position < len(records):
        header = records[position].lstrip(b"\n")
        position += 1
        if not header:
            continue
        pieces = header.split()
        if len(pieces) != 5 or not pieces[0].startswith(b":") or position >= len(records):
            raise ScanError("history_metadata_invalid")
        modes = (pieces[0][1:], pieces[1])
        if any(mode not in {b"000000", b"100644", b"100755"} for mode in modes):
            raise ScanError("non_regular_history_entry")
        validate_names(names(records[position] + b"\0"))
        position += 1
        count += 1
    return count


def snapshot(repo: Path, target: Path, staged: bool) -> dict:
    if git(repo, "ls-files", "--unmerged", "-z"):
        raise ScanError("unmerged_index")
    paths = names(git(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
                  if staged else git(repo, "ls-files", "-z"))
    validate_names(paths)  # Must reject private paths before any content read.
    copied = deleted = 0
    for name in paths:
        destination = target / name
        if staged:
            mode = git(repo, "ls-files", "--stage", "--", name).split(b" ", 1)[0]
            if mode != b"100644" and mode != b"100755":
                raise ScanError("non_regular_index_entry")
            content = git(repo, "show", f":{name}")
        else:
            source = repo / name
            if not source.exists() and not source.is_symlink():
                deleted += 1
                continue
            resolved = source.resolve()
            if not resolved.is_relative_to(repo):
                raise ScanError("non_regular_working_entry")
            validate_names([resolved.relative_to(repo).as_posix()])
            chain = [source, *list(source.parents)[:len(PurePosixPath(name).parts) - 1]]
            if any(part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()) for part in chain):
                raise ScanError("non_regular_working_entry")
            if not source.is_file():
                raise ScanError("non_regular_working_entry")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if staged:
            destination.write_bytes(content)
        else:
            # Same-volume hardlinks; Gitleaks only reads these tracked regular files.
            os.link(source, destination)
        copied += 1
    return {"files": copied, "deletedTrackedFiles": deleted}


def classify_finding(item: dict, lines: list[str]) -> dict:
    # Gitleaks already redacted values. Return only identifier names and hints;
    # no Match/Secret. These hints never suppress findings.
    match = re.search(r"([A-Za-z_][A-Za-z0-9_.-]{0,99})[\"']?\s*[:=]", item.get("Match", ""))
    field = match.group(1) if match else None
    path = item["File"].lower().replace("\\", "/")
    line = lines[item["StartLine"] - 1] if 0 < item["StartLine"] <= len(lines) else ""
    scalar = re.fullmatch(r'\s*"([^"\r\n]+)"\s*:\s*"([^"\r\n]*)"\s*,?\s*', line)
    if scalar and re.fullmatch(r"[0-9a-fA-F]{64}", scalar.group(2)):
        field = PurePosixPath(scalar.group(1).replace("\\", "/")).name
        category = "hex64_file_integrity_metadata" if "." in field else "hex64_field_metadata"
    elif scalar and scalar.group(1) == "key" and re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", scalar.group(2)):
        field = "key"
        category = "uuid_request_key_context" if "requests" in path else "uuid_key_context"
    elif field and re.search(r"sha(?:1|256|384|512)|checksum|digest|hash|fingerprint", field, re.I):
        category = "digest_field_context"
    elif "/tests/" in "/" + path or "/fixtures/" in "/" + path or Path(path).name.startswith("fixture"):
        category = "synthetic_fixture_path_context"
    elif field and re.search(r"password|passwd|token|secret|credential|apikey|api_key", field, re.I):
        category = "credential_candidate"
    else:
        category = "indeterminate"
    return {"classificationHint": category, "fieldContext": field}


def invoke_scan(binary: Path, mode: str, target: Path, repo: Path, reports: Path) -> dict:
    raw = reports / f"{mode}-raw-redacted.json"
    ignore = reports / "empty.gitleaksignore"
    ignore.write_text("", "utf-8")
    command = [str(binary), "git" if mode == "history" else "dir", str(target),
               "--config", str(SOURCE / ".gitleaks.toml"), "--redact=100",
               "--ignore-gitleaks-allow", "--gitleaks-ignore-path", str(ignore),
               "--report-format", "json", "--report-path", str(raw),
               "--exit-code", str(FINDINGS), "--log-level", "error", "--no-banner", "--no-color",
               "--max-archive-depth", "0", "--max-decode-depth", "2", "--timeout", "1100"]
    if mode == "history":
        command.append("--log-opts=--all --full-history -m")
    result = run(command, repo)
    if result.returncode not in {0, FINDINGS}:
        raw.unlink(missing_ok=True)
        raise ScanError("gitleaks_scan_failed")
    try:
        findings = json.loads(raw.read_text("utf-8"))
        if not isinstance(findings, list):
            raise ScanError("report_schema_invalid")
        safe = []
        source_cache = {}
        for item in findings:
            source_name = item["File"]
            if mode == "history":
                commit = item["Commit"]
                if not re.fullmatch(r"[0-9a-f]{40,64}", commit):
                    raise ScanError("report_commit_invalid")
                key = (commit, source_name)
                if key not in source_cache:
                    source_cache[key] = git(repo, "show", f"{commit}:{source_name}").decode("utf-8", "replace").splitlines()
            else:
                source = Path(source_name)
                if not source.is_absolute():
                    source = target / source
                source_name = source.relative_to(target).as_posix()
                key = source_name
                if key not in source_cache:
                    source_cache[key] = source.read_text("utf-8", errors="replace").splitlines()
            safe.append({"ruleId": item["RuleID"], "path": source_name,
                         "startLine": item["StartLine"], "endLine": item["EndLine"],
                         **classify_finding(item, source_cache[key])})
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise ScanError("report_schema_invalid") from exc
    finally:
        raw.unlink(missing_ok=True)
    if bool(safe) != (result.returncode == FINDINGS):
        raise ScanError("report_exit_disagreement")
    output = {"mode": mode, "findingCount": len(safe), "findings": safe}
    (reports / f"{mode}.json").write_text(json.dumps(output, indent=2) + "\n", "utf-8")
    return {"mode": mode, "findingCount": len(safe)}


def scan(repo: Path, mode: str) -> tuple[dict, int]:
    binary = executable()
    actual = Path(git(repo, "rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve()
    if actual != repo:
        raise ScanError("repo_root_required")
    if mode in {"all", "history"} and git(repo, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise ScanError("shallow_history_incomplete")
    if mode in {"all", "history"}:
        validate_history_metadata(repo)
    # Private local directories are never enumerated or scanned. Reports are never uploaded.
    reports = repo / ".local" / "security" / "PRIVADOS.local" / uuid.uuid4().hex
    reports.mkdir(parents=True, exist_ok=False)
    results = []
    coverage = {}
    try:
        if mode in {"all", "history"}:
            results.append(invoke_scan(binary, "history", repo, repo, reports))
        if mode in {"all", "working", "staged"}:
            # Keep the Windows snapshot path short; tracked evidence can have long names.
            temporary = repo / ".local" / "security-snapshots"
            temporary.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="t-", dir=temporary) as folder:
                coverage = snapshot(repo, Path(folder), staged=mode == "staged")
                results.append(invoke_scan(binary, "staged" if mode == "staged" else "working",
                                           Path(folder), repo, reports))
    except (ScanError, OSError) as exc:
        result = {"status": "incomplete", "code": str(exc) if isinstance(exc, ScanError) else "snapshot_io_failed",
                  "completedScans": results, "reportDirectory": str(reports.relative_to(repo)).replace("\\", "/")}
        (reports / "summary.json").write_text(json.dumps(result, indent=2) + "\n", "utf-8")
        return result, 2
    total = sum(item["findingCount"] for item in results)
    result = {"status": "findings" if total else "clean", "version": VERSION,
              "findingCount": total, "scans": results, "coverage": coverage,
              "reportDirectory": str(reports.relative_to(repo)).replace("\\", "/"),
              "archiveTraversal": False, "scope": "all Git refs; tracked working files only" if mode == "all" else mode}
    (reports / "summary.json").write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    return result, FINDINGS if total else 0


def install_hook(repo: Path) -> dict:
    current = run(["git", "config", "--get", "core.hooksPath"], repo)
    if current.returncode == 0:
        if current.stdout.decode("utf-8").strip() == ".githooks":
            return {"status": "hook_already_enabled"}
        raise ScanError("existing_hooks_path_preserved")
    if current.returncode != 1:
        raise ScanError("hooks_config_read_failed")
    hooks = Path(git(repo, "rev-parse", "--git-path", "hooks").decode("utf-8").strip())
    if not hooks.is_absolute():
        hooks = repo / hooks
    if hooks.is_dir() and any(path.is_file() and not path.name.endswith(".sample") for path in hooks.iterdir()):
        raise ScanError("existing_hooks_preserved")
    if not (repo / ".githooks" / "pre-commit").is_file():
        raise ScanError("hook_source_missing")
    executable()  # Enabling a hook must not leave the next commit without its tool.
    git(repo, "config", "--local", "core.hooksPath", ".githooks")
    return {"status": "hook_enabled", "scope": "local_repository_only"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "scan", "install-hook"))
    parser.add_argument("--repo", type=Path, default=SOURCE)
    parser.add_argument("--mode", choices=("all", "history", "working", "staged"), default="all")
    args = parser.parse_args()
    try:
        if args.command == "install":
            result, code = install(), 0
        elif args.command == "install-hook":
            result, code = install_hook(args.repo.resolve()), 0
        else:
            result, code = scan(args.repo.resolve(), args.mode)
        print(json.dumps(result, ensure_ascii=True))
        return code
    except (ScanError, OSError, ValueError, zipfile.BadZipFile, tarfile.TarError) as exc:
        code = str(exc) if isinstance(exc, ScanError) else "operation_failed"
        print(json.dumps({"status": "incomplete", "code": code}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
