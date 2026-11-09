"""Ten LEAO-only offline controls. Never operates a VM, service, DB or live store."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import uuid


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotnet", required=True, type=Path)
    parser.add_argument("--assembly", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    if os.name != "nt" or socket.gethostname().casefold() != "leao":
        raise SystemExit("source_controls_host_excluded")
    if args.result.exists():
        raise SystemExit("result_exists")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    assembly = args.assembly.resolve(strict=True)
    if assembly.name != manifest["entrypoint"]:
        raise SystemExit("entrypoint_mismatch")
    for item in manifest["files"]:
        file = assembly.parent / item["name"]
        if file.stat().st_size != item["bytes"] or digest(file) != item["sha256"]:
            raise SystemExit("manifest_mismatch")
    environment = {
        key: value for key, value in os.environ.items()
        if not key.upper().startswith(("DOTNET_", "COR_", "CORECLR_", "COMPLUS_", "ASPNETCORE_", "RACKCLICK_", "PG"))
        and not key.lower().startswith("connectionstrings__")
    }
    environment["DOTNET_EnableDiagnostics"] = "0"
    environment["DOTNET_ROLL_FORWARD"] = "Disable"
    base = Path(r"C:\RackClick_SVR\.local") / ("f0504-controls-" + uuid.uuid4().hex)
    request = {
        "schemaVersion": 1, "operationId": str(uuid.uuid4()), "expectedHost": "LEAO",
        "baseDirectory": str(base), "installationId": str(uuid.uuid4()),
        "password": secrets.token_urlsafe(24),
    }
    controls: list[dict] = []

    def run(label: str, verb: str, data: dict | str, expected_code: str, exit_code: int = 1) -> None:
        payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=True)
        child = subprocess.run(
            [str(args.dotnet), str(assembly), verb], input=payload, text=True,
            encoding="utf-8", capture_output=True, env=environment, timeout=60,
        )
        try:
            output = json.loads(child.stdout)
        except (ValueError, TypeError):
            output = {"code": "non_json_output"}
        passed = child.returncode == exit_code and output.get("code") == expected_code and child.stderr == ""
        controls.append({"label": label, "exitCode": child.returncode, "output": output,
                         "stderrEmpty": child.stderr == "", "passed": passed})
        if not passed:
            raise AssertionError("source_control_failed:" + label)

    def no_destination() -> None:
        if base.exists():
            raise AssertionError("unexpected_source_destination")

    def files() -> dict[str, str]:
        return {str(file.relative_to(base)): digest(file) for file in base.rglob("*") if file.is_file()}

    run("unknown_verb", "unknown", {}, "usage")
    run("malformed_json", "source", "{", "input_invalid")
    run("wrong_source_host", "source", {**request, "expectedHost": "other-host"}, "host_mismatch")
    no_destination()
    run("protected_D_id", "source", {**request, "installationId": "bbd2b6c2-abaf-4964-8c12-cf8f0c4af2aa"}, "identity_invalid")
    no_destination()
    run("short_password_before_write", "source", {**request, "password": "short"}, "password_size_invalid")
    no_destination()
    run("unknown_field", "source", {**request, "extra": True}, "input_invalid")
    no_destination()
    run("source_positive", "source", request, "", exit_code=0)
    before = files()
    run("source_existing_rejected", "source", request, "source_exists")
    preserved = before == files()
    if not preserved:
        raise AssertionError("existing_source_changed")
    target = {
        "schemaVersion": 1, "operationId": request["operationId"], "expectedHost": "LEAO",
        "baseDirectory": "C:\\ProgramData\\RackClick-F0504-" + request["operationId"],
        "originInstallationId": request["installationId"], "installationId": str(uuid.uuid4()),
        "serviceName": "UnusedF0504", "expectedServiceSid": "S-1-5-21-1-2-3-1001", "factorsSha256": "0" * 64,
    }
    run("recover_excludes_LEAO", "recover", {**target, "custodianSid": "S-1-5-32-545",
        "password": request["password"], "envelopeSha256": "0" * 64, "adaptDestinationInstallation": True}, "target_host_excluded")
    run("verify_excludes_LEAO", "verify", {**target, "expectedProcessId": 1,
        "expectedProcessStartUtc": "2026-11-03T00:00:00Z"}, "target_host_excluded")
    report = {"schemaVersion": 1, "controls": controls, "allPassed": True,
              "sourceExistingFilesPreserved": preserved, "targetVMExecuted": False,
              "secretRequestOrPasswordRecorded": False, "fixturePreserved": True}
    with args.result.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=True, indent=2)
        stream.write("\n")
    print(json.dumps({"allPassed": True, "controls": len(controls), "vmOperated": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
