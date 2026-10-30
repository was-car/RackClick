"""Scope and fail-closed refresh tests; never open the real lab/private tree."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("rackclick_cbm", Path(__file__).parents[1] / "codebase_memory.py")
cbm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cbm)


class ScopeTests(unittest.TestCase):
    def test_only_allowlisted_source_is_selected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            included = "development/server/src/App.cs"
            for name in [included, ".local/secret.cs", "RackClick-backup-all.json",
                         "development/server/src/bin/Hidden.cs", "development/server/src/credentials/Secret.cs",
                         "development/server/src/appsettings.Local.json", "evidence/history.py"]:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("FAKE_SCOPE_SENTINEL", encoding="utf-8")
            selected = [p.relative_to(root).as_posix() for p in cbm.selected_files(root)]
            self.assertEqual([included], selected)

    def test_walk_errors_abort(self):
        with self.assertRaises(PermissionError):
            cbm.walk_error(PermissionError("fixture denied"))

    def test_walk_has_error_handler(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "development/server/src").mkdir(parents=True)
            def failing_walk(*args, **kwargs):
                kwargs["onerror"](PermissionError("fixture denied"))
                return iter(())
            with patch.object(cbm.os, "walk", side_effect=failing_walk):
                with self.assertRaises(PermissionError):
                    cbm.selected_files(root)

    def test_junction_source_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "development/server/src"
            parent.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            (outside / "Hidden.cs").write_text("fake", encoding="utf-8")
            link = parent / "linked"
            command = "New-Item -ItemType Junction -Path '" + str(link).replace("'", "''") + "' -Target '" + str(outside).replace("'", "''") + "' | Out-Null"
            subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], check=True, capture_output=True)
            try:
                with self.assertRaises(ValueError):
                    cbm.selected_files(root)
            finally:
                link.rmdir()  # Remove only the generated junction, never its target.

    def test_status_requires_ready_project_and_root(self):
        for value in ["{}", '{"isError":true}', '{"content":[{"type":"text","text":"status: ready"}]}']:
            with self.subTest(value=value), patch.object(cbm, "cli", return_value=subprocess.CompletedProcess([], 0, value)):
                self.assertFalse(cbm.index_ready())

    def test_missing_native_index_forces_reindex_and_failed_index_does_not_update_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "repository"
            source.mkdir()
            native = base / "cbm.exe"
            native.write_bytes(b"fake executable never launched")
            patches = {"BASE": base, "MIRROR": base / "source", "BINARY": native, "REPOSITORY": source}
            with patch.multiple(cbm, **patches), patch.object(cbm, "selected_files", return_value=[]):
                success = subprocess.CompletedProcess([], 0, json.dumps({"structuredContent": {"project": cbm.PROJECT, "status": "indexed"}}), "")
                with patch.object(cbm, "index_ready", return_value=True), patch.object(cbm, "cli", return_value=success):
                    cbm.refresh()
                before = (base / "source-state.json").read_bytes()
                failure = subprocess.CompletedProcess([], 0, '{"isError":true}', "")
                with patch.object(cbm, "index_ready", return_value=False), patch.object(cbm, "cli", return_value=failure) as call:
                    with self.assertRaises(RuntimeError):
                        cbm.refresh()
                    self.assertEqual("index_repository", call.call_args.args[0])
                self.assertEqual(before, (base / "source-state.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
