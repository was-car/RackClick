"""Build the pinned, internal Windows bundle without builds, downloads or installation.

Only explicit files and the two curated archive slices are read. The ZIP and its
evidence directory are exclusive outputs; failed outputs are retained for diagnosis.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import BinaryIO, Callable
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APPLICATION_SHA256 = "b7b26834ac5186792a01014b7221f4ba94940da19efafb84546ca635f868fa00"
APPLICATION_XLSX_SHA256 = "cf51b03c80ddec460944295daf09705f3dbdec0cd83e054f5bfc6592fb081685"
APPLICATION_CONFIG_SHA256 = "c818294e27a40c94fe2ebf603709c94263820af1facca9a7d5c288cb70e8158e"
APPLICATION_SHARED_SHA256 = "66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9"
APPLICATION_PREFERENCES_SHA256 = "f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd"
APPLICATION_RC9_EXCEL_SHA256 = "511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5"
APPLICATION_RELATIONS_SHA256 = "1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09"
APPLICATION_PORT_COLORS_SHA256 = "b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda"
APPLICATION_CATEGORY_COLORS_SHA256 = "c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c"
APPLICATION_ONBOARDING_SHA256 = "dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b"
APPLICATION_GROUP_LINKS_SHA256 = "38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6"
APPLICATION_GROUP_RECEIPT_SHA256 = "55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6"
# Candidata 14 revisada por Codex (23.10.2026). Sus metadatos entran en el bundle con hash fijado.
APPLICATION_SCHEMA14_SHA256 = "2ec9105661db0f5c9a97d58e2a7f44e69bfd7e1903493b72f0fc57cc94c4b71a"
APPLICATION_SCHEMA14_INVENTORY_SHA256 = "9303ebd4d1e2075cbf144ae868ec10568b02f754eb4f3d95f33faffa91094086"
APPLICATION_SCHEMA14_SUMS_SHA256 = "47089172d9b7a13adb409b38289fc0ecee98866f0345810762de008e16b19b50"
# Candidata 14 limpia de D14-05: DLL 19c94d4e…, invalidación de desafíos en la recuperación; sin cambios de C2. Metadatos propios.
APPLICATION_SCHEMA14D05_SHA256 = "e9c58c0c67500afc09c1ac979a7433830c96f94c2a2e4501d81286796d65d74d"
APPLICATION_SCHEMA14D05_SUMS_SHA256 = "932588056beb49fb1a7d1627b41a85829833f029f2429a0d695a5cb77c1bf31b"
# Candidata15 congelada por el coordinador, dashboard MFA y gracia45. No es adopción.
APPLICATION_SCHEMA15_SHA256 = "294b61577ed7aa8fe68ddb1ecd6c4f11a20b4f03935c11a22404009aec6a00fb"
APPLICATION_SCHEMA15_INVENTORY_SHA256 = "4afec995adf7c403632c59c68cf694756af626e57b4d386423d1b3d7b3f1d56b"
APPLICATION_SCHEMA15_SUMS_SHA256 = "783eb1960103426b00f33e43fa2a9183d1efa4875da27b15636b35585eae662a"
APPLICATION_SCHEMA43P3_SHA256 = "d352c04381cd4f1954aa43735e540970b295f231106560c5c9880c7ee1dc78db"
APPLICATION_SCHEMA43P3_INVENTORY_SHA256 = "dbc527827b7e13e300666f8a8893bea53dd708b122b1d8be21d15b878290a452"
APPLICATION_SCHEMA43P3_SUMS_SHA256 = "2bc0fc54c6498e45225bb9313f8efc7f9ee8e27fa4149b24bfe547bb6f503aa6"
# New SQL-protected application43 for internal review; not installation approval.
APPLICATION_SCHEMA43_SQL_SHA256 = "29685419d0746df89777a5da72d25f5b7ac0e571e30decec1888787fe5f0f950"
APPLICATION_SCHEMA43_SQL_INVENTORY_SHA256 = "86ad16f9295fbd71c6aae78a403a2c336e15d284897ae4216d341b8d040ef40c"
APPLICATION_SCHEMA43_SQL_SUMS_SHA256 = "e2cb5728431bfa51bf66d2d4b17760a8d70a3d66a30595ead24bc39cf5e8baac"
# Closed pinned manifests, not caller-provided version/hash overrides or adoption.
APPLICATION_SCHEMA45_SQL_SHA256 = "528a03d2efc939d1cea631b1caa9f3e6a445e44257fa757f87a95691acfb6933"
APPLICATION_SCHEMA45_SQL_INVENTORY_SHA256 = "75b9a378560072c841afea83d305384780244bdb8b258c39de0cf29d17359930"
APPLICATION_SCHEMA45_SQL_SUMS_SHA256 = "b623c46ba133d515765ad74bfaf6f7d1d8acdb4d784bbe84296b95e4e0557c56"
# F0401 writer integrated into the same closed SQL-protected schema45 family.
APPLICATION_SCHEMA45_MFA_SHA256 = "a2ec1c7d3570593297a63b672ee485489e49ed0658ff49f6d2ef585803f6a8af"
APPLICATION_SCHEMA45_MFA_INVENTORY_SHA256 = "cfaf7ea2629c9bafcfa550bac07dedaad3ec1062a5e006f692c28bb915c4ec52"
APPLICATION_SCHEMA45_MFA_SUMS_SHA256 = "cac5516551740a24eef010a3157d691f2e61ab4bdaad69da3a1a7dd02cc470d2"

APPLICATION_PROFILES = {
    APPLICATION_SCHEMA45_MFA_SHA256: {"name": "45-sql", "files": {"server": 55, "frontend": 18}, "bytes": 25870874,
                                      "metadata": {"inventory.json": APPLICATION_SCHEMA45_MFA_INVENTORY_SHA256,
                                                   "SHA256SUMS.txt": APPLICATION_SCHEMA45_MFA_SUMS_SHA256}},
    APPLICATION_SCHEMA45_SQL_SHA256: {"name": "45-sql", "files": {"server": 55, "frontend": 18}, "bytes": 25867806,
                                      "metadata": {"inventory.json": APPLICATION_SCHEMA45_SQL_INVENTORY_SHA256,
                                                   "SHA256SUMS.txt": APPLICATION_SCHEMA45_SQL_SUMS_SHA256}},
    APPLICATION_SCHEMA43_SQL_SHA256: {"name": "43-sql", "files": {"server": 53, "frontend": 18}, "bytes": 25650673,
                                      "metadata": {"inventory.json": APPLICATION_SCHEMA43_SQL_INVENTORY_SHA256,
                                                   "SHA256SUMS.txt": APPLICATION_SCHEMA43_SQL_SUMS_SHA256}},
    APPLICATION_SCHEMA43P3_SHA256: {"name": "43", "files": {"server": 53, "frontend": 18}, "bytes": 25638925,
                                    "metadata": {"inventory.json": APPLICATION_SCHEMA43P3_INVENTORY_SHA256,
                                                 "SHA256SUMS.txt": APPLICATION_SCHEMA43P3_SUMS_SHA256}},
    APPLICATION_SCHEMA15_SHA256: {"name": "15", "files": {"server": 25, "frontend": 18}, "bytes": 8007063,
                                  "metadata": {"inventory.json": APPLICATION_SCHEMA15_INVENTORY_SHA256,
                                               "SHA256SUMS.txt": APPLICATION_SCHEMA15_SUMS_SHA256}},
    APPLICATION_SCHEMA14_SHA256: {"name": "14", "files": {"server": 24, "frontend": 18}, "bytes": 7263552,
                                  "metadata": {"inventory.json": APPLICATION_SCHEMA14_INVENTORY_SHA256,
                                               "SHA256SUMS.txt": APPLICATION_SCHEMA14_SUMS_SHA256}},
    APPLICATION_SCHEMA14D05_SHA256: {"name": "14", "files": {"server": 24, "frontend": 18}, "bytes": 7489372,
                                    "metadata": {"inventory.json": APPLICATION_SCHEMA14_INVENTORY_SHA256,
                                                 "SHA256SUMS.txt": APPLICATION_SCHEMA14D05_SUMS_SHA256}},
    APPLICATION_SHA256: {"name": "337", "files": {"server": 18, "frontend": 18}, "bytes": 6578061},
    APPLICATION_XLSX_SHA256: {"name": "397", "files": {"server": 18, "frontend": 18}, "bytes": 6653702},
    APPLICATION_CONFIG_SHA256: {"name": "532", "files": {"server": 18, "frontend": 18}, "bytes": 6794984},
    APPLICATION_SHARED_SHA256: {"name": "592", "files": {"server": 19, "frontend": 18}, "bytes": 6939574},
    APPLICATION_PREFERENCES_SHA256: {"name": "712", "files": {"server": 20, "frontend": 18}, "bytes": 7028507},
    APPLICATION_RC9_EXCEL_SHA256: {"name": "832", "files": {"server": 20, "frontend": 18}, "bytes": 7108267},
    APPLICATION_RELATIONS_SHA256: {"name": "849", "files": {"server": 20, "frontend": 18}, "bytes": 7108622},
    APPLICATION_PORT_COLORS_SHA256: {"name": "969", "files": {"server": 21, "frontend": 18}, "bytes": 7037914},
    APPLICATION_CATEGORY_COLORS_SHA256: {"name": "1089", "files": {"server": 22, "frontend": 18}, "bytes": 7133395},
    APPLICATION_ONBOARDING_SHA256: {"name": "1209", "files": {"server": 22, "frontend": 18}, "bytes": 7146303},
    APPLICATION_GROUP_LINKS_SHA256: {"name": "1329", "files": {"server": 22, "frontend": 18}, "bytes": 7148383},
    APPLICATION_GROUP_RECEIPT_SHA256: {"name": "1449", "files": {"server": 22, "frontend": 18}, "bytes": 7159235}}
VERSIONS = {"schema": 9, "dotnetRuntime": "10.0.12", "postgresql": "17.11",
            "vcRedist": "14.51.36247.0", "vcRuntimeMinimum": "14.44.35211.0"}
ARCHIVE_PINS = {
    "dotnet": ("10.0.401", "dotnet-sdk-10.0.401-win-x64.zip", "SHA512",
               "24b670ad3d923bfcf47df6c3b034152398b42f6dbc388e10d783aee1cfb5e5817d399fc0ae2a12cfa822a55e61d34830ccb15c50ef6efee437ab874bb7c79430"),
    "postgresql": ("17.11", "postgresql-17.11-4-windows-x64-binaries.zip", "SHA256",
                   "b9424ee7bc60b52450ff910a3630225df32e633f3cb29c1d126d9299d59aea28")}
SOURCE_PINS = {
    "vc_redist.x64.exe": (18731856, "843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c"),
    "Npgsql-LICENSE": (903, "2e1d9cc6ed4eb7fe6fa82091846c06b4f58571a2c3b54777db6baeca10dd2d74")}
# Lock exclusivo de 14 (development/offline-bundle14.sources.json). El histórico 9–13 no cambia.
SOURCE_PINS_14 = {**SOURCE_PINS, "Otp.NET-LICENSE": (1070, "0bc32be0ce13330ba88d208548582a641f95b1f66bb19be91f5acc1436c52472")}
SOURCE_KEYS = {"vc_redist.x64.exe": "vcRedistSha256", "Npgsql-LICENSE": "npgsqlLicenseSha256",
               "Otp.NET-LICENSE": "otpNetLicenseSha256"}
SOURCE_TARGETS = {"vc_redist.x64.exe": "prerequisites/vc_redist.x64.exe", "Npgsql-LICENSE": "licenses/Npgsql-LICENSE",
                  "Otp.NET-LICENSE": "licenses/Otp.NET-LICENSE.txt"}
OPERATORS = (
    "Invoke-RackClickPrivateDeployment.ps1", "New-RackClickDatabaseBackup.ps1",
    "New-RackClickPrivateDeployment.ps1", "New-RackClickLabInstance.ps1",
    "New-RackClickRecoveredInstance.ps1", "New-RackClickLabHttpsProfile.ps1",
    "Test-ServerDistribution.ps1", "Test-StagedDistribution.ps1", "Test-RuntimePrerequisites.ps1",
    "Test-RackClickPrivateDeployment.ps1", "Stop-RackClickLabInstance.ps1",
    "Start-RackClickLabInstance.ps1", "Stage-ServerDistribution.ps1",
    "Restore-RackClickPrivateDeployment.ps1",
    "RackClick.Stage.ps1", "RackClick.Process.ps1", "RackClick.Process.Gate.ps1",
    "RackClick.LaunchControl.ps1", "RackClick.Instance.ps1", "RackClick.Https.ps1",
    "RackClick.Deployment.ps1", "RackClick.Backup.ps1", "RackClick.OfflineBundle.ps1",
    "Test-RackClickOfflineBundle.ps1", "Install-RackClickOfflineBundle.ps1")
SQL_OPERATORS = OPERATORS + ("RackClick.SqlSecrets.ps1",)
MANUALS = ("MANUAL-PAQUETE-WINDOWS-S1.md", "CONSTRUIR-PAQUETE-WINDOWS-S1.md",
           "OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md", "RECUPERACION-DESPLIEGUE-WINDOWS-S1.md")
PG_NOTICES = ("commandlinetools_3rd_party_licenses.txt", "pgAdmin_3rd_party_licenses.txt",
              "pgAdmin_license.txt", "server_license.txt", "StackBuilder_3rd_party_licenses.txt")
LICENSE_NOTICE = b"""RackClick internal Windows validation bundle; no publication or adoption approval.
Official .NET notices are preserved in dependencies/dotnet/LICENSE.txt and
ThirdPartyNotices.txt. PostgreSQL's five original root notices are preserved in
dependencies/postgresql; these include notices for components not selected here.
Frontend licenses remain in application/frontend/licenses. Npgsql's complete
903-byte LICENSE is preserved here from its pinned upstream commit.
Preserving notices alone does not close LGPL obligations or redistribution rights.
Microsoft VC++ redistribution rights and all third-party obligations require review
before publication, redistribution or adoption. No System32 DLLs were copied.
The VC++ executable is preserved unchanged; this producer never executes it.
"""
MAX_ZIP = 512 * 1024 * 1024
MAX_FILE = 256 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024
MAX_FILES = 10000
HEX256 = re.compile(r"[0-9a-f]{64}\Z")
RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
            *(f"lpt{i}" for i in range(1, 10))}


class BundleError(ValueError):
    """A sanitized, stable error code; never print private source paths."""


def require(ok: bool, code: str) -> None:
    if not ok:
        raise BundleError(code)


def application_schema(manifest_sha256: str) -> int:
    require(manifest_sha256 in APPLICATION_PROFILES, "application_pin_mismatch")
    if manifest_sha256 in (APPLICATION_SCHEMA45_SQL_SHA256, APPLICATION_SCHEMA45_MFA_SHA256):
        return 45
    if manifest_sha256 in (APPLICATION_SCHEMA43P3_SHA256, APPLICATION_SCHEMA43_SQL_SHA256):
        return 43
    if APPLICATION_PROFILES[manifest_sha256]["name"] == "15":
        return 15
    if manifest_sha256 in (APPLICATION_SCHEMA14_SHA256, APPLICATION_SCHEMA14D05_SHA256):
        return 14
    if manifest_sha256 in (APPLICATION_CATEGORY_COLORS_SHA256, APPLICATION_ONBOARDING_SHA256, APPLICATION_GROUP_LINKS_SHA256, APPLICATION_GROUP_RECEIPT_SHA256):
        return 13
    if manifest_sha256 == APPLICATION_PORT_COLORS_SHA256:
        return 12
    if manifest_sha256 in (APPLICATION_PREFERENCES_SHA256, APPLICATION_RC9_EXCEL_SHA256, APPLICATION_RELATIONS_SHA256):
        return 11
    return 10 if manifest_sha256 == APPLICATION_SHARED_SHA256 else 9


def operator_names(manifest_sha256: str) -> tuple[str, ...]:
    require(manifest_sha256 in APPLICATION_PROFILES, "application_pin_mismatch")
    return SQL_OPERATORS if APPLICATION_PROFILES[manifest_sha256]["name"] in {"43-sql", "45-sql"} else OPERATORS


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def strict_json(data: bytes) -> dict:
    def pairs(items):
        result = {}
        for name, value in items:
            require(name not in result, "json_duplicate_key")
            result[name] = value
        return result
    try:
        result = json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(BundleError("json_invalid")))
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, BundleError):
            raise
        raise BundleError("json_invalid") from exc
    require(isinstance(result, dict), "json_object_required")
    return result


def safe_name(name: str) -> str:
    require(isinstance(name, str) and 0 < len(name) <= 240 and name.isascii(), "path_unsafe")
    require(all(32 <= ord(c) < 127 and c not in '<>:"\\|?*~' for c in name), "path_unsafe")
    parts = name.split("/")
    require(all(p and p not in (".", "..") and len(p) <= 255 and
                not p.endswith((" ", ".")) and p.split(".")[0].lower() not in RESERVED
                for p in parts), "path_unsafe")
    return name


def validate_names(names: list[str]) -> None:
    seen: set[str] = set()
    spellings: dict[str, str] = {}
    for name in names:
        key = safe_name(name).lower()
        require(key not in seen, "path_collision")
        seen.add(key)
        parts = name.split("/")
        for i in range(1, len(parts) + 1):
            prefix = "/".join(parts[:i])
            require(spellings.setdefault(prefix.lower(), prefix) == prefix, "path_collision")
    for key in seen:
        parts = key.split("/")
        require(not any("/".join(parts[:i]) in seen for i in range(1, len(parts))), "path_collision")


def clean_path(path: Path, *, exists: bool = True, directory: bool = False) -> Path:
    """Reject symlinks/junctions at every existing ancestor before resolving."""
    absolute = Path(os.path.abspath(path))
    for item in (*reversed(absolute.parents), absolute):
        if not os.path.lexists(item):
            continue
        info = item.lstat()
        require(not stat.S_ISLNK(info.st_mode) and
                not (getattr(info, "st_file_attributes", 0) & 0x400), "reparse_path_rejected")
    if exists:
        require(absolute.is_dir() if directory else absolute.is_file(), "source_missing_or_wrong_type")
    return absolute


def workspace_path(name: str) -> Path:
    safe_name(name)
    result = clean_path(ROOT / name)
    require(result.is_relative_to(ROOT), "source_outside_workspace")
    return result


def hash_stream(stream: BinaryIO, algorithm: str = "sha256") -> str:
    result = hashlib.new(algorithm.lower())
    stream.seek(0)
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        result.update(chunk)
    stream.seek(0)
    return result.hexdigest()


@contextmanager
def locked_archive_read(path: Path):
    """Windows denies concurrent writes/deletes for the entire hash/select interval."""
    if os.name != "nt":
        # The supported producer execution/verification environment is Windows.
        raise BundleError("producer_windows_required")
    import ctypes
    from ctypes import wintypes
    import msvcrt
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    handle = create(str(path), 0x80000000, 1, None, 3, 0x80, None)  # READ, SHARE_READ, OPEN_EXISTING
    require(handle != wintypes.HANDLE(-1).value, "archive_read_lock_failed")
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except Exception:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(handle)
        raise
    with os.fdopen(descriptor, "rb") as stream:
        yield stream


def read_file(path: Path, limit: int = MAX_FILE) -> bytes:
    path = clean_path(path)
    require(path.stat().st_size <= limit, "source_too_large")
    with path.open("rb") as stream:
        value = stream.read(limit + 1)
    require(len(value) <= limit, "source_too_large")
    return value


@dataclass(frozen=True)
class Payload:
    path: str
    data: bytes

    def record(self) -> dict:
        return {"bytes": len(self.data), "sha256": hashlib.sha256(self.data).hexdigest()}


def archive_inventory(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    """Validate even unselected names; never extract or follow an archive link."""
    files = {}
    all_names: set[str] = set()
    directories: set[str] = set()
    for info in archive.infolist():
        directory = info.is_dir()
        name = info.filename[:-1] if directory else info.filename
        safe_name(name)
        key = name.lower()
        require(key not in all_names, "archive_entry_collision")
        all_names.add(key)
        mode = (info.external_attr >> 16) & 0xFFFF
        require(not stat.S_ISLNK(mode) and stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR) and
                not (info.external_attr & 0x400) and not (info.flag_bits & 1), "archive_entry_unsupported")
        if directory:
            directories.add(key)
        else:
            require(0 <= info.file_size <= MAX_FILE, "archive_entry_too_large")
            files[name] = info
    file_keys = {n.lower() for n in files}
    require(not (file_keys & directories), "archive_entry_collision")
    for key in all_names:
        parts = key.split("/")
        require(not any("/".join(parts[:i]) in file_keys for i in range(1, len(parts))), "archive_entry_collision")
    # Includes implicit directory spelling, so Windows does not merge a/x and A/y.
    validate_names(list(files))
    return files


def runtime_selection(name: str) -> bool:
    return name in ("dotnet.exe", "LICENSE.txt", "ThirdPartyNotices.txt") or name.startswith((
        "host/fxr/10.0.12/", "shared/Microsoft.NETCore.App/10.0.12/", "shared/Microsoft.AspNetCore.App/10.0.12/"))


def postgres_selection(name: str) -> bool:
    return name in ("pgsql/" + n for n in PG_NOTICES) or name.startswith(("pgsql/bin/", "pgsql/lib/", "pgsql/share/"))


def archive_slice(archive: zipfile.ZipFile, predicate: Callable[[str], bool], prefix: str,
                  strip: str, expected_count: int, expected_bytes: int) -> list[Payload]:
    inventory = archive_inventory(archive)
    selected = [i for n, i in inventory.items() if predicate(n)]
    require(len(selected) == expected_count and sum(i.file_size for i in selected) == expected_bytes,
            "archive_slice_inventory_mismatch")
    return [Payload(prefix + i.filename.removeprefix(strip), archive.read(i)) for i in selected]


def collect_application(manifest_path: Path, expected_sha: str) -> tuple[list[Payload], Path]:
    require(isinstance(expected_sha, str) and expected_sha in APPLICATION_PROFILES, "application_pin_mismatch")
    profile = APPLICATION_PROFILES[expected_sha]
    raw = read_file(manifest_path, 8 * 1024 * 1024)
    require(hashlib.sha256(raw).hexdigest() == expected_sha, "application_manifest_untrusted")
    manifest = strict_json(raw)
    schema = application_schema(expected_sha)
    require(manifest.get("schema") == schema and type(manifest.get("schema")) is int, "application_schema_mismatch")
    distributions = manifest.get("distributions")
    require(isinstance(distributions, dict) and set(distributions) == {"server", "frontend"}, "application_inventory_invalid")
    if profile['name'] == '45-sql':
        pinned_45 = {
            APPLICATION_SCHEMA45_SQL_SHA256: ('.local/distribution45/sql-01/manifest.json', 'schema45-sql-protected-01'),
            APPLICATION_SCHEMA45_MFA_SHA256: ('.local/distribution45/mfa-store-01/manifest.json', 'schema45-mfa-store-01'),
        }
        expected_path, expected_profile = pinned_45[expected_sha]
        require(manifest_path == ROOT / expected_path, "application_root_invalid")
        require(manifest.get('profileId') == expected_profile, "application_profile_mismatch")
        candidate = clean_path(manifest_path.parent, directory=True)
    elif profile['name'] == '43-sql':
        require(manifest_path == ROOT / '.local/sql-integracion-12/distribution/manifest.json',
                "application_root_invalid")
        require(manifest.get('profileId') == 'schema43-sql-protected-01', "application_profile_mismatch")
        candidate = clean_path(manifest_path.parent, directory=True)
    elif schema >= 14:
        # Cada esquema moderno tiene su área propia; nunca se recorre todo .local.
        require(manifest_path.name == "manifest.json" and manifest_path.parent.parent == ROOT / f".local/distribution{schema}",
                "application_root_invalid")
        candidate = clean_path(manifest_path.parent, directory=True)
    else:
        candidate_name = manifest.get("candidateDirectory")
        require(isinstance(candidate_name, str), "application_root_invalid")
        safe_name(candidate_name)
        candidate = clean_path(ROOT / candidate_name, directory=True)
        require(candidate.is_relative_to(ROOT / ".local/candidates"), "application_root_invalid")
    result = [Payload("application/manifest.json", raw)]
    for kind, expected in distributions.items():
        require(isinstance(expected, dict) and len(expected) == profile["files"][kind], "application_inventory_invalid")
        validate_names(list(expected))
        root = clean_path(candidate / kind, directory=True)
        actual = []
        # Walk only the two explicitly identified distribution directories, never ROOT/.local.
        pending = [root]
        while pending:
            current = pending.pop()
            with os.scandir(current) as entries:
                for entry in entries:
                    child = clean_path(Path(entry.path), directory=entry.is_dir(follow_symlinks=False))
                    if child.is_dir():
                        pending.append(child)
                    else:
                        actual.append(child.relative_to(root).as_posix())
        validate_names(actual)
        require(set(actual) == set(expected), "application_inventory_mismatch")
        for name, digest in expected.items():
            require(isinstance(digest, str) and HEX256.fullmatch(digest), "application_digest_invalid")
            data = read_file(root / name)
            require(hashlib.sha256(data).hexdigest() == digest, "application_file_untrusted")
            result.append(Payload(f"application/{kind}/{name}", data))
    require(sum(len(p.data) for p in result[1:]) == profile["bytes"], "application_bytes_mismatch")
    # Metadatos fijados de la candidata: van al bundle con su hash, pero no cuentan como bytes de distribución.
    for name, digest in profile.get("metadata", {}).items():
        path = clean_path(candidate / name, exists=False)
        require(path.is_file(), "application_metadata_missing")
        data = read_file(path, 8 * 1024 * 1024)
        require(hashlib.sha256(data).hexdigest() == digest, "application_metadata_untrusted")
        result.append(Payload(f"application/{name}", data))
    return result, candidate


def collect_locks(sources_path: Path, pins: dict = SOURCE_PINS, lock_profile: str = "legacy") -> tuple[dict, dict, list[Payload], list[dict], list[Path]]:
    source_data = read_file(sources_path, 1024 * 1024)
    sources = strict_json(source_data)
    require(sources.get("schemaVersion") == 1 and sources.get("internalOnly") is True,
            "sources_lock_invalid")
    # Un lock de un perfil no sirve para el otro: el 14 exige 'lockProfile': '14'; los históricos no lo declaran.
    require(sources.get("lockProfile", "legacy") == lock_profile, "sources_profile_mismatch")
    require(all(sources.get(k) == v for k, v in VERSIONS.items() if k != "schema"), "sources_version_mismatch")
    require(sources.get("sourceToolchainLock") == "development/toolchain.lock.json", "toolchain_path_invalid")
    toolchain_path = workspace_path(sources["sourceToolchainLock"])
    toolchain = strict_json(read_file(toolchain_path, 1024 * 1024))
    require(toolchain.get("schemaVersion") == 1 and toolchain.get("platform") == "win-x64", "toolchain_invalid")
    components = toolchain.get("components")
    require(isinstance(components, list) and all(isinstance(c, dict) for c in components), "toolchain_invalid")
    by_id = {c.get("id"): c for c in components}
    require(len(by_id) == len(components), "toolchain_duplicate_component")
    for key, values in ARCHIVE_PINS.items():
        component = by_id.get(key, {})
        require(tuple(component.get(p) for p in ("version", "archive", "hashAlgorithm", "hash")) == values,
                "toolchain_pin_mismatch")
    rows = sources.get("sources")
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows) and len(rows) == len(pins),
            "sources_inventory_invalid")
    by_name = {r.get("name"): r for r in rows}
    require(len(by_name) == len(rows) and set(by_name) == set(pins), "sources_inventory_invalid")
    result, report, paths = [], [], [toolchain_path]
    for name, (size, digest) in pins.items():
        row = by_name[name]
        require(type(row.get("bytes")) is int and row["bytes"] == size and row.get("sha256") == digest,
                "source_pin_mismatch")
        # Mapa explícito por origen: cada fuente tiene su clave de hash de nivel superior, sin inferirla del nombre.
        require(sources.get(SOURCE_KEYS[name]) == digest, "source_pin_mismatch")
        path = workspace_path(row.get("path"))
        data = read_file(path)
        require(len(data) == size and hashlib.sha256(data).hexdigest() == digest, "source_file_untrusted")
        result.append(Payload(SOURCE_TARGETS[name], data))
        report.append({"name": name, "bytes": size, "sha256": digest})
        paths.append(path)
    return sources, by_id, result, report, paths


def validate_outputs(destination: Path, evidence: Path, source_files: list[Path], source_roots: list[Path]) -> tuple[Path, Path]:
    destination, evidence = clean_path(destination, exists=False), clean_path(evidence, exists=False)
    require(destination.suffix.lower() == ".zip", "destination_zip_required")
    require(not os.path.lexists(destination) and not os.path.lexists(evidence), "output_exists")
    clean_path(destination.parent, directory=True)
    clean_path(evidence.parent, directory=True)
    require(destination != evidence and not destination.is_relative_to(evidence) and
            not evidence.is_relative_to(destination), "outputs_overlap")
    for output in (destination, evidence):
        for source in source_files:
            require(output != source and not source.is_relative_to(output), "output_overlaps_source")
        for root in source_roots:
            require(not output.is_relative_to(root) and not root.is_relative_to(output), "output_overlaps_source")
    return destination, evidence


def write_bundle(payloads: list[Payload], application_sha: str, destination: Path) -> dict:
    versions = {**VERSIONS, "schema": application_schema(application_sha)}
    validate_names([p.path for p in payloads] + ["bundle.json"])
    require(len(payloads) + 1 <= MAX_FILES and all(len(p.data) <= MAX_FILE for p in payloads) and
            sum(len(p.data) for p in payloads) <= MAX_TOTAL, "bundle_limits_exceeded")
    records = {p.path: p.record() for p in sorted(payloads, key=lambda p: p.path)}
    identity = hashlib.sha256(json_bytes({"versions": versions,
                              "applicationManifestSha256": application_sha, "files": records})).hexdigest()
    manifest = {"schemaVersion": 1, "kind": "RackClickOfflineBundle",
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "urn:rackclick:offline-bundle:" + identity)),
                "platform": "win-x64", "versions": versions,
                "applicationManifestSha256": application_sha, "files": records}
    manifest_data = json_bytes(manifest)
    all_payloads = sorted([*payloads, Payload("bundle.json", manifest_data)], key=lambda p: p.path)
    # 'xb' is CreateNew. Keep the file, including on error; never replace an existing output.
    with destination.open("xb") as output:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9,
                             strict_timestamps=True) as archive:
            for payload in all_payloads:
                info = zipfile.ZipInfo(payload.path, (1980, 1, 1, 0, 0, 0))
                info.create_system = 0
                info.create_version = 20
                info.extract_version = 20
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0x20  # DOS archive, no executable/link/platform mode bits.
                info.internal_attr = 0
                info.flag_bits = 0
                info.extra = b""
                info.comment = b""
                archive.writestr(info, payload.data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        output.flush()
        os.fsync(output.fileno())
    require(destination.stat().st_size <= MAX_ZIP, "bundle_zip_limit_exceeded")
    with destination.open("rb") as stream:
        archive_sha = hash_stream(stream)
    return {"schemaVersion": 1, "valid": True, "code": "internal_bundle_created",
            "bundleId": manifest["id"], "bundleArchiveSha256": archive_sha,
            "bundleManifestSha256": hashlib.sha256(manifest_data).hexdigest(),
            "applicationManifestSha256": application_sha, "archiveBytes": destination.stat().st_size,
            "files": len(all_payloads), "payloadBytes": sum(len(p.data) for p in all_payloads),
            "versions": versions, "internalOnly": True,
            "redistributionRightsReview": "open", "adopted": False}


def build(manifest: Path, expected_manifest_sha: str, sdk_archive: Path, postgres_archive: Path,
          sources_lock: Path, destination: Path, evidence: Path) -> dict:
    require(isinstance(expected_manifest_sha, str) and HEX256.fullmatch(expected_manifest_sha), "manifest_sha_invalid")
    sources_lock, manifest = clean_path(sources_lock), clean_path(manifest)
    sdk_archive, postgres_archive = clean_path(sdk_archive), clean_path(postgres_archive)
    application, candidate = collect_application(manifest, expected_manifest_sha)
    # 14 y15 usan las mismas dependencias pinadas en el lock14; 9–13 conservan el histórico.
    pins, lock_profile = (SOURCE_PINS_14, "14") if application_schema(expected_manifest_sha) >= 14 else (SOURCE_PINS, "legacy")
    _, components, external, source_report, extra_paths = collect_locks(sources_lock, pins, lock_profile)
    selected_operators = operator_names(expected_manifest_sha)
    operators = [workspace_path("tools/windows/" + n) for n in selected_operators]
    operator_payloads = [Payload("operators/" + p.name, read_file(p)) for p in operators]
    # Archived 25-operator ZIPs retain their closed reader profile. Building a new
    # legacy ZIP from today's SQL-dependent sources must fail before output.
    require("RackClick.SqlSecrets.ps1" in selected_operators or
            not any(b"RackClick.SqlSecrets.ps1" in p.data for p in operator_payloads),
            "operator_dependency_missing")
    manuals = [workspace_path("docs/" + n) for n in MANUALS]
    destination, evidence = validate_outputs(destination, evidence,
        [manifest, sources_lock, sdk_archive, postgres_archive, *extra_paths, *operators, *manuals],
        [candidate, ROOT / "tools", ROOT / "docs", ROOT / "development", ROOT / ".local/downloads"])
    # Hold the exact checked archive handles until selection has finished. No extraction on disk.
    with ExitStack() as stack:
        handles = {}
        for key, path in (("dotnet", sdk_archive), ("postgresql", postgres_archive)):
            component = components[key]
            require(path.name == component["archive"], "archive_filename_mismatch")
            handle = stack.enter_context(locked_archive_read(path))
            digest = hash_stream(handle, component["hashAlgorithm"])
            require(digest == component["hash"], "archive_untrusted")
            handles[key] = handle
            source_report.append({"name": path.name, "bytes": path.stat().st_size,
                                  "hashAlgorithm": component["hashAlgorithm"], "hash": digest})
        sdk = stack.enter_context(zipfile.ZipFile(handles["dotnet"]))
        pg = stack.enter_context(zipfile.ZipFile(handles["postgresql"]))
        runtime = archive_slice(sdk, runtime_selection, "dependencies/dotnet/", "", 339, 110497993)
        postgres = archive_slice(pg, postgres_selection, "dependencies/postgresql/", "pgsql/", 1568, 141177651)
    payloads = [*application, *external, *runtime, *postgres,
                Payload("licenses/README.txt", LICENSE_NOTICE),
                *operator_payloads,
                *(Payload("docs/" + p.name, read_file(p)) for p in manuals)]
    validate_names([p.path for p in payloads])
    # Reserve evidence only after every source and inventory has passed. Error evidence is retained.
    evidence.mkdir(exist_ok=False)
    try:
        report = write_bundle(payloads, expected_manifest_sha, destination)
        report["sources"] = sorted(source_report, key=lambda r: r["name"])
        profile = APPLICATION_PROFILES[expected_manifest_sha]
        report["slices"] = {"application": {"files": sum(profile["files"].values()), "bytes": profile["bytes"]},
                            "dotnet": {"files": 339, "bytes": 110497993},
                            "postgresql": {"files": 1568, "bytes": 141177651},
                            "operators": {"files": len(selected_operators)}, "manuals": {"files": len(MANUALS)}}
        with (evidence / "REPORT.json").open("xb") as stream:
            stream.write(json_bytes(report))
        with (evidence / "SHA256SUMS.txt").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(report["bundleArchiveSha256"] + "  " + destination.name + "\n")
        return report
    except Exception:
        with (evidence / "FAILED.json").open("xb") as stream:
            stream.write(json_bytes({"valid": False, "code": "bundle_write_failed", "partialRetained": True}))
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha", required=True)
    parser.add_argument("--sdk-archive", type=Path, required=True)
    parser.add_argument("--postgres-archive", type=Path, required=True)
    parser.add_argument("--sources-lock", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build(args.manifest, args.expected_manifest_sha, args.sdk_archive, args.postgres_archive,
                       args.sources_lock, args.destination, args.evidence)
    except Exception as exc:
        code = str(exc) if isinstance(exc, BundleError) else "io_or_archive_error"
        print(json.dumps({"valid": False, "code": code}))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
