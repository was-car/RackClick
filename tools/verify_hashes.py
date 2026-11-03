"""Read-only SHA-256/ZIP verifier for explicitly selected release artifacts.

Example (the report directory must already exist):
  python -B tools/verify_hashes.py --root PACKAGE --manifest SHA256SUMS.txt \
      --zip reference.zip --report evidence/new-report.json

Exit codes: 0 = verified; 1 = failed verification (including invalid inputs);
2 = CLI/report error. Reports are created exclusively and never overwritten.
Names in a filesystem manifest are relative to --root. Names in a ZIP manifest
are relative to that manifest's directory. ZIPs are inspected, never extracted.
Extra members are reported, not treated as hash mismatches: manifests normally
exclude themselves. This verifies integrity, not publisher authenticity.
"""

import argparse
import hashlib
import json
import platform
import re
import stat
import sys
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def file_sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_name(name, *, directory=False):
    """Use an unambiguous portable path, including on case-insensitive Windows."""
    if name.startswith("./"):
        name = name[2:]
    if directory and name.endswith("/"):
        name = name[:-1]
    if not name or any(ord(c) < 32 for c in name) or any(c in name for c in '\\:<>"|?*'):
        raise ValueError(f"Unsafe path: {name!r}")
    parts = name.split("/")
    for part in parts:
        if part in ("", ".", "..") or part.endswith((".", " ")):
            raise ValueError(f"Unsafe path: {name!r}")
        if re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", part.split(".")[0], re.I):
            raise ValueError(f"Reserved Windows path: {name!r}")
    return "/".join(parts)


def records(raw):
    result = []
    seen = set()
    for number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](.+)", line)
        if not match:
            raise ValueError(f"Invalid checksum line {number}")
        name = safe_name(match[2])
        if name.casefold() in seen:
            raise ValueError(f"Duplicate manifest path at line {number}: {name}")
        seen.add(name.casefold())
        result.append((name, match[1].lower()))
    if not result:
        raise ValueError("Empty checksum manifest")
    return result


def checked(name, expected, observed, size=None):
    return dict(path=name, expected=expected, observed=observed, size=size,
                status="MATCH" if observed == expected else
                ("MISSING" if observed is None else "MISMATCH"))


def error(report, code, path, detail):
    report["errors"].append(dict(code=code, path=str(path), detail=str(detail)))


def verify_files(root, manifest, report, protected):
    section = dict(path=str(manifest), rows=[])
    report["manifest"] = section
    protected.add(manifest)
    try:
        raw = manifest.read_bytes()
        section["sha256"] = sha256(raw)
        entries = records(raw)
    except (OSError, ValueError) as exc:
        error(report, "INVALID_MANIFEST", manifest, exc)
        return
    for name, expected in entries:
        target = root / name
        protected.add(target)
        try:
            resolved = target.resolve()
            protected.add(resolved)
            if not resolved.is_relative_to(root):
                raise ValueError("Manifest target resolves outside --root")
            if target.is_file():
                row = checked(name, expected, file_sha256(target), target.stat().st_size)
            else:
                row = checked(name, expected, None)
            section["rows"].append(row)
            if row["status"] != "MATCH":
                error(report, row["status"], name, "Filesystem checksum failed")
        except (OSError, ValueError) as exc:
            error(report, "UNREADABLE_OR_UNSAFE_FILE", name, exc)


def verify_zip(archive, report):
    section = dict(path=str(archive), manifests=[], duplicate_entries=[], crc_failure=None)
    report["zip_archives"].append(section)
    try:
        section["sha256"] = file_sha256(archive)
        with zipfile.ZipFile(archive) as z:
            members = {}
            seen = set()
            invalid = False
            for info in z.infolist():
                try:
                    # orig_filename preserves NULs that ZipInfo.filename truncates.
                    name = safe_name(info.orig_filename, directory=info.is_dir())
                    if stat.S_ISLNK(info.external_attr >> 16):
                        raise ValueError("ZIP symbolic links are not supported")
                    if name.casefold() in seen:
                        section["duplicate_entries"].append(info.orig_filename)
                        raise ValueError("Duplicate or case-colliding ZIP entry")
                    seen.add(name.casefold())
                    if not info.is_dir():
                        members[name] = info
                except ValueError as exc:
                    invalid = True
                    error(report, "UNSAFE_OR_DUPLICATE_ZIP_ENTRY", info.orig_filename, exc)
            if invalid:
                return
            section["crc_failure"] = z.testzip()
            if section["crc_failure"]:
                error(report, "ZIP_CRC_FAILURE", section["crc_failure"], "ZIP CRC check failed")
                return
            manifests = sorted(n for n in members if PurePosixPath(n).name.startswith("SHA256SUMS"))
            if not manifests:
                error(report, "ZIP_MANIFEST_MISSING", archive, "No SHA256SUMS manifest found in ZIP")
            for manifest_name in manifests:
                entry = dict(path=manifest_name, rows=[], unlisted_members=[])
                section["manifests"].append(entry)
                try:
                    rows = records(z.read(members[manifest_name]))
                except (OSError, ValueError) as exc:
                    error(report, "INVALID_ZIP_MANIFEST", manifest_name, exc)
                    continue
                prefix = str(PurePosixPath(manifest_name).parent)
                prefix = "" if prefix == "." else prefix + "/"
                covered = set()
                for name, expected in rows:
                    target = prefix + name
                    covered.add(target)
                    info = members.get(target)
                    if info is None:
                        row = checked(target, expected, None)
                    else:
                        with z.open(info) as stream:
                            observed = hashlib.file_digest(stream, "sha256").hexdigest()
                        row = checked(target, expected, observed, info.file_size)
                    entry["rows"].append(row)
                    if row["status"] != "MATCH":
                        error(report, "ZIP_" + row["status"], target, "ZIP checksum failed")
                entry["unlisted_members"] = sorted(n for n in members if n.startswith(prefix) and n not in covered)
    except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, zlib.error) as exc:
        error(report, "UNREADABLE_OR_INVALID_ZIP", archive, exc)


def rooted(root, path):
    return (path if path.is_absolute() else root / path).resolve()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, required=True, help="Root directory of the explicitly selected package")
    parser.add_argument("--manifest", type=Path, required=True, help="Absolute path, or path relative to --root")
    parser.add_argument("--zip", type=Path, action="append", default=[], help="ZIP to verify, absolute or relative to --root; repeatable")
    parser.add_argument("--report", type=Path, required=True, help="New JSON report path; existing files are never overwritten")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest = rooted(root, args.manifest)
    archives = [rooted(root, archive) for archive in args.zip]
    destination = args.report.resolve()
    # Check before reading or writing. Open with 'x' below also closes the race.
    if destination.exists() or args.report.is_symlink():
        print("Report path already exists; choose a new report path.", file=sys.stderr)
        return 2
    protected = {manifest, *archives}
    report = dict(generated_utc=datetime.now(timezone.utc).isoformat(),
                  scope="Explicit input manifests and archives; no input is modified or extracted",
                  platform=platform.platform(), python=sys.version, root=str(root),
                  manifest=None, zip_archives=[], errors=[])
    if not root.is_dir():
        error(report, "INVALID_ROOT", root, "--root must be an existing directory")
    else:
        verify_files(root, manifest, report, protected)
        for archive in archives:
            verify_zip(archive, report)
    if destination in protected:
        print("Report path collides with an input path; choose a separate report path.", file=sys.stderr)
        return 2
    report["status"] = "FAIL" if report["errors"] else "PASS"
    rows = (report["manifest"] or {}).get("rows", [])
    zip_rows = [row for archive in report["zip_archives"] for manifest in archive["manifests"] for row in manifest["rows"]]
    report["counts"] = dict(files=len(rows), files_matched=sum(r["status"] == "MATCH" for r in rows),
                            zip_files=len(zip_rows), zip_files_matched=sum(r["status"] == "MATCH" for r in zip_rows),
                            errors=len(report["errors"]))
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as output:
            output.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"Cannot create report: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(dict(status=report["status"], counts=report["counts"], report=str(destination))))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
