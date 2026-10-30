"""Real pinned scanner and hook, isolated Git repositories; synthetic secrets only."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "tools" / "security" / "secret_scan.py"
spec = importlib.util.spec_from_file_location("rackclick_secret_scan", SCRIPT)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


class SecretScannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scanner.executable()  # Absence is a failure, never a passing skipped scan.
        cls.fixture_parent = ROOT / ".local" / "security-test-fixtures"
        cls.fixture_parent.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fake-", dir=self.fixture_parent)
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.hooksPath", str(self.repo / "unused-hooks"))
        (self.repo / ".gitignore").write_text(".local/\nPRIVADOS.local/\n", "utf-8")
        (self.repo / "readme.txt").write_text("safe fixture\n", "utf-8")
        self.git("add", ".gitignore", "readme.txt")
        self.git("commit", "-qm", "synthetic baseline")
        # Assemble a nonfunctional synthetic key at runtime, never a complete key in source.
        self.fake = "ghp_" + "aB3dE5fG7hJ9kL2mN4pQ6rS8tU0vW1xY3zA5"

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, "isolated git setup failed")
        return result.stdout

    def call(self, mode="all"):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), "scan", "--repo", str(self.repo),
                               "--mode", mode], capture_output=True, check=False)

    def test_clean_scan_covers_history_and_working_without_private_content(self):
        private = self.repo / "PRIVADOS.local"
        private.mkdir()
        (private / "do-not-read.txt").write_text(self.fake, "utf-8")
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        summary = json.loads(result.stdout)
        self.assertEqual([scan["mode"] for scan in summary["scans"]], ["history", "working"])
        self.assertEqual(summary["coverage"]["files"], 2)
        self.assertNotIn(self.fake.encode(), result.stdout + result.stderr)

    def test_deleted_historical_secret_still_blocks_and_reports_metadata_only(self):
        (self.repo / "fixture.txt").write_text("token = " + self.fake + "\n", "utf-8")
        self.git("add", "fixture.txt")
        self.git("commit", "-qm", "synthetic positive fixture")
        self.git("rm", "-q", "fixture.txt")
        self.git("commit", "-qm", "remove synthetic fixture")
        result = self.call()
        self.assertEqual(result.returncode, 10, result.stderr.decode())
        self.assertNotIn(self.fake.encode(), result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        reports = self.repo / summary["reportDirectory"]
        text = "".join(path.read_text("utf-8") for path in reports.glob("*.json"))
        self.assertNotIn(self.fake, text)
        self.assertNotIn("fixture@example.invalid", text)
        history = json.loads((reports / "history.json").read_text("utf-8"))
        self.assertGreater(history["findingCount"], 0)
        self.assertEqual(set(history["findings"][0]),
                         {"ruleId", "path", "startLine", "endLine", "classificationHint", "fieldContext"})
        self.assertFalse(list(reports.glob("*raw*")))

    def test_staged_content_blocks_even_when_working_copy_clean(self):
        path = self.repo / "fixture.txt"
        path.write_text("token = " + self.fake + " # gitleaks:allow\n", "utf-8")
        self.git("add", "fixture.txt")
        path.write_text("safe working copy\n", "utf-8")
        result = self.call("staged")
        self.assertEqual(result.returncode, 10, result.stderr.decode())
        self.assertNotIn(self.fake.encode(), result.stdout + result.stderr)
        self.assertEqual(self.call("working").returncode, 0)

    def test_tracked_working_secret_blocks_and_untracked_is_not_read(self):
        (self.repo / "readme.txt").write_text("token = " + self.fake + "\n", "utf-8")
        (self.repo / "untracked-private.txt").write_text(self.fake, "utf-8")
        result = self.call("working")
        self.assertEqual(result.returncode, 10)
        self.assertEqual(json.loads(result.stdout)["coverage"]["files"], 2)

    def test_private_staged_path_rejected_before_content_read(self):
        (self.repo / "admin-login.json").write_text(json.dumps({"token": self.fake}), "utf-8")
        self.git("add", "admin-login.json")
        with patch.object(scanner, "git", wraps=scanner.git) as wrapped:
            with self.assertRaisesRegex(scanner.ScanError, "private_or_unsafe_tracked_path"):
                scanner.snapshot(self.repo, self.repo / "snapshot", staged=True)
            self.assertFalse(any(call.args[1] == "show" for call in wrapped.call_args_list))

    def test_private_diagnostics_and_windows_escaped_paths_are_rejected(self):
        for name in ("trace.binlog", "process.dmp", "C:/outside/file.txt", "C:outside.txt",
                     "../outside.txt", "folder\\file.txt", "//host/share/file.txt"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(scanner.ScanError, "private_or_unsafe_tracked_path"):
                    scanner.validate_names([name])

    def test_triage_distinguishes_file_hash_uuid_and_credential_without_values(self):
        cases = [
            ('"Secrets.cs": "' + 'a' * 64 + '",', "hex64_file_integrity_metadata"),
            ('"key": "00000000-1111-4222-8333-444444444444",', "uuid_request_key_context"),
            ('"password": "' + self.fake + '",', "credential_candidate"),
        ]
        for line, category in cases:
            field = line.split('"')[1]
            item = {"File": "evidence/requests.json", "StartLine": 1,
                    "Match": '"' + field + '": "REDACTED"'}
            result = scanner.classify_finding(item, [line])
            self.assertEqual(result["classificationHint"], category)
            self.assertNotIn(self.fake, json.dumps(result))
            self.assertNotIn('a' * 64, json.dumps(result))

    def test_deleted_private_history_rejected_before_scanner_all_and_history(self):
        (self.repo / "admin-login.json").write_text(json.dumps({"token": self.fake}), "utf-8")
        self.git("add", "admin-login.json")
        self.git("commit", "-qm", "synthetic private file")
        self.git("rm", "-q", "admin-login.json")
        self.git("commit", "-qm", "remove synthetic private file")
        for mode in ("all", "history"):
            with patch.object(scanner, "invoke_scan") as invoke:
                with self.assertRaisesRegex(scanner.ScanError, "private_or_unsafe_tracked_path"):
                    scanner.scan(self.repo, mode)
                invoke.assert_not_called()
        result = self.call("history")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(self.fake.encode(), result.stdout + result.stderr)

    def test_merge_only_introduced_secret_is_in_history_scope(self):
        original = self.git("branch", "--show-current").decode().strip()
        self.git("branch", "other")
        (self.repo / "main.txt").write_text("safe main branch\n", "utf-8")
        self.git("add", "main.txt")
        self.git("commit", "-qm", "main branch fixture")
        self.git("checkout", "-q", "other")
        (self.repo / "other.txt").write_text("safe other branch\n", "utf-8")
        self.git("add", "other.txt")
        self.git("commit", "-qm", "other branch fixture")
        self.git("checkout", "-q", original)
        self.git("merge", "--no-commit", "--no-ff", "other")
        (self.repo / "merge-only.txt").write_text("token = " + self.fake + "\n", "utf-8")
        self.git("add", "merge-only.txt")
        self.git("commit", "-qm", "synthetic secret introduced only by merge")
        result = self.call("history")
        self.assertEqual(result.returncode, 10, result.stderr.decode())
        self.assertNotIn(self.fake.encode(), result.stdout + result.stderr)

    def test_missing_or_tampered_tool_blocks_without_fallback(self):
        fake_cache = self.repo / "missing-tool"
        with patch.object(scanner, "CACHE", fake_cache):
            with self.assertRaisesRegex(scanner.ScanError, "gitleaks_missing"):
                scanner.executable()
        fake_cache.mkdir()
        selected = scanner.asset()
        (fake_cache / selected["name"]).write_bytes(b"tampered synthetic archive")
        binary = fake_cache / ("gitleaks.exe" if os.name == "nt" else "gitleaks")
        binary.write_bytes(b"not executable")
        with patch.object(scanner, "CACHE", fake_cache):
            with self.assertRaisesRegex(scanner.ScanError, "archive_checksum_mismatch"):
                scanner.executable()

    def test_existing_hook_configuration_is_preserved(self):
        before = self.git("config", "--get", "core.hooksPath")
        with self.assertRaisesRegex(scanner.ScanError, "existing_hooks_path_preserved"):
            scanner.install_hook(self.repo)
        self.assertEqual(self.git("config", "--get", "core.hooksPath"), before)

    def test_real_hook_rejects_fake_secret_and_accepts_clean_index(self):
        (self.repo / "old.txt").write_text("token = " + self.fake + "\n", "utf-8")
        self.git("add", "old.txt")
        self.git("commit", "-qm", "old synthetic secret")
        self.git("rm", "-q", "old.txt")
        self.git("commit", "-qm", "historical fixture removed")
        hooks = self.repo / ".githooks"
        hooks.mkdir()
        shutil.copy2(ROOT / ".githooks" / "pre-commit", hooks / "pre-commit")
        (hooks / "pre-commit").chmod(0o755)
        script_dir = self.repo / "tools" / "security"
        script_dir.mkdir(parents=True)
        # Hook delegates to the real workspace scanner with its verified binary.
        (script_dir / "secret_scan.py").write_text(
            "import runpy,sys\nsys.path.insert(0," + repr(str(SCRIPT.parent)) + ")\n"
            "runpy.run_path(" + repr(str(SCRIPT)) + ",run_name='__main__')\n", "utf-8")
        self.git("config", "--unset", "core.hooksPath")
        scanner.install_hook(self.repo)
        self.git("add", ".githooks", "tools")
        self.git("commit", "-qm", "safe hook fixture")
        (self.repo / "fixture.txt").write_text("token = " + self.fake + "\n", "utf-8")
        self.git("add", "fixture.txt")
        result = subprocess.run(["git", "commit", "-qm", "must reject synthetic key"],
                                cwd=self.repo, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'"status": "findings"', result.stdout + result.stderr)
        self.assertNotIn(self.fake.encode(), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
