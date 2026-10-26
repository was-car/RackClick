"""Build the portable connector for existing RackClick installations, without data."""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import zipfile

KIT_NAME = "RackClick-Conectar-Aqui-01"


def build_bundle(root: Path) -> bytes:
    operators = root / "tools/windows/server-install"
    files = {
        "Set-RackClickInstanceNetwork.ps1": (operators / "Set-RackClickInstanceNetwork.ps1").read_bytes(),
        "LEEME.html": (root / "docs/RACKCLICK-CASA-Y-TRABAJO.html").read_bytes(),
    }
    launcher = (operators / "Start-RackClickHere.ps1").read_text(encoding="utf-8-sig")
    if launcher.count("@@ENGINE_SHA256@@") != 1:
        raise ValueError("Expected exactly one engine hash placeholder")
    launcher = launcher.replace(
        "@@ENGINE_SHA256@@",
        hashlib.sha256(files["Set-RackClickInstanceNetwork.ps1"]).hexdigest(),
    )
    if "@@" in launcher:
        raise ValueError("Unresolved launcher placeholder")
    files["Start-RackClickHere.ps1"] = launcher.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8-sig")
    files["00-ABRIR-RACKCLICK.cmd"] = (
        '@echo off\r\nsetlocal\r\n'
        'echo RackClick - Conectar en casa o en el trabajo\r\n'
        'echo Utiliza este acceso dentro de la VM donde esta instalado RackClick.\r\n'
        '"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -STA -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-RackClickHere.ps1"\r\n'
        'set "RackClickResult=%ERRORLEVEL%"\r\n'
        'if "%RackClickResult%"=="0" exit /b 0\r\n'
        'echo No se ha confirmado la conexion. Consulta la ventana y el informe del Escritorio.\r\n'
        'pause\r\nexit /b %RackClickResult%\r\n'
    ).encode("ascii")
    files["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n"
        for name, data in sorted(files.items())
    ).encode("ascii")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(KIT_NAME + "/" + name, (2026, 10, 22, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    return stream.getvalue()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    blob = build_bundle(Path(__file__).resolve().parents[2])
    with args.output.open("xb") as target:
        target.write(blob)
    print(f"{hashlib.sha256(blob).hexdigest()}  {args.output} ({len(blob)} bytes)")
