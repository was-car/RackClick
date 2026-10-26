"""Build the fixed-instance network recovery kit; never include installation data."""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import zipfile


def build_bundle(root: Path, kit_version: int = 3) -> bytes:
    if kit_version not in (3, 4):
        raise ValueError("Unsupported repair kit")
    operators = root / "tools/windows/server-install"
    files = {
        "RackClick-Cambiar-IP-02.ps1": (operators / "Set-RackClickServerNetwork.ps1").read_bytes(),
        "Repair-RackClickNetworkTransaction.ps1": (operators / "Repair-RackClickNetworkTransaction.ps1").read_bytes(),
        "LEEME.html": (root / f"docs/REPARAR-RED-{kit_version:02d}.html").read_bytes(),
    }
    launcher = (operators / "Start-RackClickNetworkRepair.ps1").read_text(encoding="utf-8-sig")
    launcher = launcher.replace("@@NETWORK_SHA256@@", hashlib.sha256(files["RackClick-Cambiar-IP-02.ps1"]).hexdigest())
    launcher = launcher.replace("@@REPAIR_SHA256@@", hashlib.sha256(files["Repair-RackClickNetworkTransaction.ps1"]).hexdigest())
    if "@@" in launcher:
        raise ValueError("Unresolved launcher pin")
    files["Start-RackClickNetworkRepair.ps1"] = launcher.encode("utf-8-sig")
    files["00-REPARAR-RED.cmd"] = (
        '@echo off\r\nsetlocal\r\n'
        'echo RackClick - Reparar el intento pendiente y cambiar a 192.168.250.78\r\n'
        'echo Ejecute este archivo como administrador en la VM de RackClick.\r\n'
        '"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-RackClickNetworkRepair.ps1"\r\n'
        'set "RackClickResult=%ERRORLEVEL%"\r\n'
        'echo.\r\necho Codigo final: %RackClickResult%\r\n'
        'echo El resultado JSON se guarda en el Escritorio, si esta disponible.\r\n'
        'pause\r\nexit /b %RackClickResult%\r\n'
    ).encode("ascii")
    files["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n"
        for name, data in sorted(files.items())
    ).encode("ascii")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(f"RackClick-Reparar-Red-{kit_version:02d}/" + name, (2026, 10, 20, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    return stream.getvalue()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kit-version", type=int, choices=(3, 4), default=3)
    args = parser.parse_args()
    blob = build_bundle(Path(__file__).resolve().parents[2], args.kit_version)
    with args.output.open("xb") as target:
        target.write(blob)
    print(f"{hashlib.sha256(blob).hexdigest()}  {args.output} ({len(blob)} bytes)")
