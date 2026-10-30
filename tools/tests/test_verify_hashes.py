"""Synthetic subprocess regressions; no original manifests or references are edited."""

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "verify_hashes.py"


def checksum(name, data=b"correct payload"):
    return f"{hashlib.sha256(data).hexdigest()}  {name}\n"


class VerifyHashesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rackclick-hashes-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "package"
        self.root.mkdir()
        self.manifest = self.root / "SHA256SUMS.txt"
        self.manifest.write_text(checksum("file.txt"), encoding="utf-8")
        (self.root / "file.txt").write_bytes(b"correct payload")
        self.report = self.base / "report.json"

    def run_check(self, *, archives=(), report=None):
        # Includes missing inputs implicitly: creation of any payload file fails
        # this snapshot comparison. Only the explicitly selected report is output.
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        command = [sys.executable, "-B", str(SCRIPT), "--root", str(self.root),
                   "--manifest", "SHA256SUMS.txt", "--report", str(report or self.report)]
        for archive in archives:
            command.extend(["--zip", str(archive)])
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=20)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after, "Verifier changed its input package")
        parsed = json.loads(self.report.read_text(encoding="utf-8")) if self.report.exists() else None
        return result, parsed

    def make_zip(self, *, payload=b"correct payload", name="package/file.txt", extra=()):
        archive = self.root / "reference.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as z:
            z.writestr("package/SHA256SUMS.txt", checksum("file.txt"))
            if payload is not None:
                z.writestr(name, payload)
            for member, data in extra:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    z.writestr(member, data)
        # On Windows zipfile normalizes backslashes when writing. Inject the
        # deliberately invalid spelling into both same-length ZIP headers.
        for member, _ in extra:
            if "\\" in member:
                raw = archive.read_bytes()
                archive.write_bytes(raw.replace(member.replace("\\", "/").encode(), member.encode()))
        return archive

    def assert_error(self, parsed, code):
        self.assertEqual(parsed["status"], "FAIL")
        self.assertIn(code, [e["code"] for e in parsed["errors"]])

    def test_valid_files_and_zip_return_zero_without_modifying_inputs(self):
        result, parsed = self.run_check(archives=[self.make_zip()])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(parsed["status"], "PASS")
        self.assertEqual(parsed["counts"], dict(files=1, files_matched=1, zip_files=1, zip_files_matched=1, errors=0))

    def test_missing_file_returns_one(self):
        (self.root / "file.txt").unlink()
        result, parsed = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "MISSING")

    def test_altered_file_returns_one(self):
        (self.root / "file.txt").write_bytes(b"altered")
        result, parsed = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "MISMATCH")

    def test_invalid_manifest_returns_nonzero(self):
        self.manifest.write_text("not a hash manifest\n", encoding="utf-8")
        result, parsed = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "INVALID_MANIFEST")

    def test_empty_manifest_cannot_succeed(self):
        self.manifest.write_text("\n", encoding="utf-8")
        result, parsed = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "INVALID_MANIFEST")

    def test_non_utf8_manifest_returns_nonzero(self):
        self.manifest.write_bytes(b"\xff\xfe")
        result, parsed = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "INVALID_MANIFEST")

    def test_missing_manifest_returns_nonzero(self):
        self.manifest.unlink()
        result, parsed = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "INVALID_MANIFEST")

    def test_duplicate_manifest_path_is_rejected(self):
        self.manifest.write_text(checksum("file.txt") + checksum("FILE.txt"), encoding="utf-8")
        result, parsed = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "INVALID_MANIFEST")

    def test_unsafe_manifest_paths_are_rejected(self):
        for name in ("../outside", "/outside", "C:/outside", "file.txt:stream", "a\\b", "NUL", "a/../b", "file.txt."):
            with self.subTest(path=name):
                self.manifest.write_text(checksum(name), encoding="utf-8")
                result, parsed = self.run_check()
                self.assertEqual(result.returncode, 1)
                self.assert_error(parsed, "INVALID_MANIFEST")
                self.report.unlink()

    def test_bom_uppercase_digest_and_binary_marker_are_supported(self):
        line = checksum("./file.txt").replace("  ", " *")
        self.manifest.write_text(line[:64].upper() + line[64:], encoding="utf-8-sig")
        result, parsed = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(parsed["status"], "PASS")

    def test_unicode_filename_is_supported(self):
        (self.root / "file.txt").rename(self.root / "puerto-ä-数据.txt")
        self.manifest.write_text(checksum("puerto-ä-数据.txt"), encoding="utf-8")
        result, parsed = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(parsed["status"], "PASS")

    def test_zip_missing_member_returns_one(self):
        result, parsed = self.run_check(archives=[self.make_zip(payload=None)])
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "ZIP_MISSING")

    def test_zip_altered_member_returns_one(self):
        result, parsed = self.run_check(archives=[self.make_zip(payload=b"altered")])
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "ZIP_MISMATCH")

    def test_zip_corrupt_crc_returns_one(self):
        archive = self.make_zip()
        with zipfile.ZipFile(archive) as z:
            offset = z.getinfo("package/file.txt").header_offset
        data = bytearray(archive.read_bytes())
        name_len, extra_len = struct.unpack_from("<HH", data, offset + 26)
        data[offset + 30 + name_len + extra_len] ^= 1
        archive.write_bytes(data)
        result, parsed = self.run_check(archives=[archive])
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "ZIP_CRC_FAILURE")

    def test_duplicate_zip_member_returns_one(self):
        result, parsed = self.run_check(archives=[self.make_zip(extra=[("package/file.txt", b"duplicate")])])
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "UNSAFE_OR_DUPLICATE_ZIP_ENTRY")

    def test_case_colliding_zip_member_returns_one(self):
        result, parsed = self.run_check(archives=[self.make_zip(extra=[("package/FILE.txt", b"duplicate")])])
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "UNSAFE_OR_DUPLICATE_ZIP_ENTRY")

    def test_unsafe_zip_member_returns_one(self):
        for name in ("../outside.txt", "/absolute.txt", "C:/outside.txt", "dir\\file.txt", "file.txt:stream"):
            with self.subTest(path=name):
                self.report.unlink(missing_ok=True)
                result, parsed = self.run_check(archives=[self.make_zip(extra=[(name, b"unsafe")])])
                self.assertEqual(result.returncode, 1)
                self.assert_error(parsed, "UNSAFE_OR_DUPLICATE_ZIP_ENTRY")
                self.report.unlink()

    def test_zip_symlink_is_rejected(self):
        archive = self.make_zip()
        info = zipfile.ZipInfo("package/link")
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        with zipfile.ZipFile(archive, "a") as z:
            z.writestr(info, "../../outside")
        result, parsed = self.run_check(archives=[archive])
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "UNSAFE_OR_DUPLICATE_ZIP_ENTRY")

    def test_invalid_zip_returns_one(self):
        archive = self.root / "bad.zip"
        archive.write_bytes(b"not a ZIP")
        result, parsed = self.run_check(archives=[archive])
        self.assertEqual(result.returncode, 1)
        self.assert_error(parsed, "UNREADABLE_OR_INVALID_ZIP")

    def test_zip_manifest_invalid_or_missing_is_rejected(self):
        for name, data, code in (("SHA256SUMS.txt", "invalid", "INVALID_ZIP_MANIFEST"),
                                 ("unrelated.txt", "some bytes", "ZIP_MANIFEST_MISSING")):
            with self.subTest(name=name):
                archive = self.root / "bad.zip"
                with zipfile.ZipFile(archive, "w") as z:
                    z.writestr(name, data)
                result, parsed = self.run_check(archives=[archive])
                self.assertEqual(result.returncode, 1)
                self.assert_error(parsed, code)
                self.report.unlink()

    def test_report_cannot_overwrite_manifest(self):
        result, parsed = self.run_check(report=self.manifest)
        self.assertEqual(result.returncode, 2)
        self.assertIsNone(parsed)

    def test_report_cannot_create_missing_input(self):
        target = self.root / "file.txt"
        target.unlink()
        result, parsed = self.run_check(report=target)
        self.assertEqual(result.returncode, 2)
        self.assertIsNone(parsed)
        self.assertFalse(target.exists())

    def test_report_cannot_overwrite_previous_report(self):
        self.report.write_text('{"preserved": true}\n', encoding="utf-8")
        result, parsed = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(parsed, dict(preserved=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
