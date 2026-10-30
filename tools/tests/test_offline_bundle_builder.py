"""Focused producer checks with isolated synthetic fixtures; no DB or installer.

Real pinned packaging is explicitly opt-in, run twice only after sources freeze.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("package_offline_bundle", ROOT / "tools/package_offline_bundle.py")
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from offline_profile_matrix import MATRIX  # noqa: E402  Expectativas literales, no calculadas por el producto.


class OfflineBundleBuilder(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rackclick-bundle-unit-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def rejects(self, code, operation):
        with self.assertRaises(builder.BundleError) as caught:
            operation()
        self.assertEqual(str(caught.exception), code)

    @contextmanager
    def archive(self, entries):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as output:
            for name, data in entries:
                output.writestr(name, data)
        buffer.seek(0)
        with zipfile.ZipFile(buffer) as source:
            yield source

    def test_01_windows_names_traversal_ads_reserved_and_collisions(self):
        for name in ("../secret", "/absolute", "C:/file", "a\\b", "a//b", "a/./b", "a/../b",
                     "a:stream", "A/NUL.txt", "com1", "LPT9.log", "x.", "x ", "x/", "x\x00y", "é", "SHORT~1"):
            with self.subTest(name=name):
                self.rejects("path_unsafe", lambda: builder.safe_name(name))
        for names in (("A.txt", "a.txt"), ("x", "x/child"), ("a/x", "A/y")):
            self.rejects("path_collision", lambda: builder.validate_names(list(names)))

    def test_02_archive_rejects_unselected_ambiguity_and_links(self):
        for entries, code in (
            ([("safe/file", b"ok"), ("../unselected", b"bad")], "path_unsafe"),
            ([("safe/file", b"one"), ("SAFE/FILE", b"two")], "archive_entry_collision"),
            ([("safe", b"file"), ("safe/child", b"child")], "archive_entry_collision"),
            ([("safe/", b""), ("SAFE", b"file")], "archive_entry_collision")):
            with self.archive(entries) as archive:
                self.rejects(code, lambda: builder.archive_slice(archive, lambda n: n == "safe/file", "out/", "", 1, 2))
        link = zipfile.ZipInfo("safe/link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.archive([(link, b"outside")]) as archive:
            self.rejects("archive_entry_unsupported", lambda: builder.archive_inventory(archive))

    def test_03_slices_select_only_runtime_and_postgres_not_sdk(self):
        entries = [("dotnet.exe", b"host"), ("LICENSE.txt", b"license"), ("ThirdPartyNotices.txt", b"notices"),
                   ("host/fxr/10.0.12/hostfxr.dll", b"fxr"),
                   ("shared/Microsoft.NETCore.App/10.0.12/a.dll", b"net"),
                   ("shared/Microsoft.AspNetCore.App/10.0.12/b.dll", b"asp"),
                   ("sdk/10.0.401/private.txt", b"not runtime"), ("shared/Microsoft.NETCore.App/9.0.0/a.dll", b"old")]
        with self.archive(entries) as archive:
            selected = builder.archive_slice(archive, builder.runtime_selection, "dependencies/dotnet/", "", 6, 27)
        self.assertEqual(len(selected), 6)
        self.assertFalse(any("sdk/" in p.path or "9.0.0" in p.path for p in selected))
        entries = [("pgsql/bin/a.exe", b"a"), ("pgsql/lib/b.dll", b"b"), ("pgsql/share/c.txt", b"c"),
                   *(("pgsql/" + n, b"notice") for n in builder.PG_NOTICES),
                   ("pgsql/pgAdmin4/private", b"excluded"), ("pgsql/StackBuilder/run.exe", b"excluded")]
        with self.archive(entries) as archive:
            selected = builder.archive_slice(archive, builder.postgres_selection, "pg/", "pgsql/", 8, 33)
        self.assertEqual(len(selected), 8)
        self.assertTrue(all("pg/pgsql/" not in p.path for p in selected))

    def test_04_json_duplicates_and_schema_pins_fail_closed(self):
        self.rejects("json_duplicate_key", lambda: builder.strict_json(b'{"x":1,"x":2}'))
        source = json.loads((ROOT / "development/offline-bundle.sources.json").read_bytes())
        source["vcRedist"] = "0.0"
        target = self.home / "sources.json"
        target.write_bytes(builder.json_bytes(source))
        self.rejects("sources_version_mismatch", lambda: builder.collect_locks(target))
        self.rejects("application_pin_mismatch", lambda: builder.collect_application(self.home / "absent", "0" * 64))
        fake = self.home / "manifest.json"
        fake.write_bytes(b"{}")
        self.rejects("application_manifest_untrusted", lambda: builder.collect_application(fake, builder.APPLICATION_SHA256))

    def test_05_output_exclusive_disjoint_and_existing_unchanged(self):
        source = self.home / "input"; source.mkdir()
        sentinel = source / "sentinel"; sentinel.write_bytes(b"secret fixture; never selected")
        before = sha(sentinel)
        self.rejects("output_overlaps_source", lambda: builder.validate_outputs(
            source / "out.zip", self.home / "evidence", [sentinel], [source]))
        existing = self.home / "existing.zip"; existing.write_bytes(b"keep me")
        self.rejects("output_exists", lambda: builder.validate_outputs(existing, self.home / "ev", [], []))
        # Pin conocido (14) para llegar a la exclusividad del archivo; el pin desconocido tiene su propia prueba.
        with self.assertRaises(FileExistsError):
            builder.write_bundle([builder.Payload("allowed/file", b"ok")], builder.APPLICATION_SCHEMA14_SHA256, existing)
        self.assertEqual(existing.read_bytes(), b"keep me")
        self.assertEqual(sha(sentinel), before)
        self.assertFalse((self.home / "ev").exists())

    def test_06_synthetic_zip_reproducible_and_inventory_complete(self):
        # Only small synthetic payloads: this is not the two real release builds.
        payloads = [builder.Payload("operators/a.ps1", b"a"), builder.Payload("docs/b.md", b"b")]
        a, b = self.home / "a.zip", self.home / "b.zip"
        report_a = builder.write_bundle(payloads, builder.APPLICATION_SCHEMA14_SHA256, a)
        report_b = builder.write_bundle(list(reversed(payloads)), builder.APPLICATION_SCHEMA14_SHA256, b)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        self.assertEqual(report_a["bundleId"], report_b["bundleId"])
        with zipfile.ZipFile(a) as archive:
            names = archive.namelist()
            self.assertEqual(names, sorted(names))
            manifest = json.loads(archive.read("bundle.json"))
            self.assertEqual(set(manifest), {"schemaVersion", "kind", "id", "platform", "versions", "applicationManifestSha256", "files"})
            self.assertEqual(set(manifest["files"]), {p.path for p in payloads})
            for info in archive.infolist():
                self.assertFalse(info.is_dir())
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual((info.flag_bits, info.create_system, info.external_attr), (0, 0, 0x20))
                if info.filename != "bundle.json":
                    self.assertEqual(manifest["files"][info.filename], {
                        "bytes": info.file_size, "sha256": hashlib.sha256(archive.read(info)).hexdigest()})
        changed = self.home / "changed.zip"
        report_c = builder.write_bundle([builder.Payload("operators/a.ps1", b"changed")], builder.APPLICATION_SCHEMA14_SHA256, changed)
        self.assertNotEqual(report_a["bundleId"], report_c["bundleId"])

    def test_06b_unknown_application_pin_is_refused_before_any_output(self):
        destination = self.home / "desconocido.zip"
        self.rejects("application_pin_mismatch", lambda: builder.write_bundle(
            [builder.Payload("operators/a.ps1", b"a")], "a" * 64, destination))
        self.assertFalse(destination.exists())

    def test_07_application_exact_tree_no_extra_or_secret_recursion(self):
        root = self.home
        candidate = root / ".local/candidates/unit"
        manifest = {"schema": 9, "candidateDirectory": ".local/candidates/unit", "distributions": {}}
        for kind in ("server", "frontend"):
            directory = candidate / kind; directory.mkdir(parents=True)
            files = {}
            for i in range(18):
                name = f"file{i}.txt"; data = bytes([i])
                (directory / name).write_bytes(data)
                files[name] = hashlib.sha256(data).hexdigest()
            manifest["distributions"][kind] = files
        secret = root / ".local/pgdata/private.key"; secret.parent.mkdir()
        secret.write_bytes(b"NEVER_READ_OR_INCLUDE")
        path = root / "manifest.json"; path.write_bytes(builder.json_bytes(manifest))
        expected = sha(path)
        original_read = builder.read_file
        reads = []
        def checked_read(path, *args):
            reads.append(path)
            return original_read(path, *args)
        with patch.object(builder, "ROOT", root), patch.object(builder, "APPLICATION_PROFILES", {
                expected: {"name": "synthetic", "files": {"server": 18, "frontend": 18}, "bytes": 6578061}}):
            # Exact tree validation precedes the production aggregate size check.
            with patch.object(builder, "read_file", checked_read):
                self.rejects("application_bytes_mismatch", lambda: builder.collect_application(path, expected))
            self.assertNotIn(secret, reads)
            (candidate / "frontend/hidden-extra").write_bytes(b"extra")
            self.rejects("application_inventory_mismatch", lambda: builder.collect_application(path, expected))
            (candidate / "frontend/hidden-extra").unlink()
            (candidate / "server/file0.txt").write_bytes(b"corrupt")
            self.rejects("application_file_untrusted", lambda: builder.collect_application(path, expected))
        self.assertEqual(secret.read_bytes(), b"NEVER_READ_OR_INCLUDE")

    def test_08_symlink_ancestor_rejected(self):
        source = self.home / "source"; source.mkdir()
        (source / "file").write_bytes(b"unchanged")
        link = self.home / "link"
        try:
            link.symlink_to(source, target_is_directory=True)
        except OSError:
            # Windows junctions do not require developer-mode symlink privileges.
            if os.name != "nt":
                raise
            import subprocess
            completed = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(source)], capture_output=True)
            self.assertEqual(completed.returncode, 0)
        self.rejects("reparse_path_rejected", lambda: builder.clean_path(link / "file"))
        # Remove only our link so TemporaryDirectory never traverses it.
        link.unlink() if link.is_symlink() else link.rmdir()
        self.assertEqual((source / "file").read_bytes(), b"unchanged")

    @unittest.skipUnless(os.name == "nt", "native Windows sharing contract")
    def test_09_archive_handle_blocks_concurrent_write_delete(self):
        source = self.home / "source.zip"; source.write_bytes(b"pinned archive fixture")
        before = sha(source)
        with builder.locked_archive_read(source) as stream:
            self.assertEqual(builder.hash_stream(stream), before)
            with self.assertRaises(PermissionError):
                with source.open("ab") as other:
                    other.write(b"mutation")
            with self.assertRaises(PermissionError):
                source.unlink()
        self.assertEqual(sha(source), before)

    @unittest.skipUnless(os.name == "nt", "native Windows sharing contract")
    def test_10_build_bad_archive_hash_never_selects_or_reserves_outputs(self):
        # Tiny synthetic archives deliberately cannot satisfy the official pins.
        sdk = self.home / builder.ARCHIVE_PINS["dotnet"][1]; sdk.write_bytes(b"untrusted synthetic SDK")
        pg = self.home / builder.ARCHIVE_PINS["postgresql"][1]; pg.write_bytes(b"untrusted synthetic PG")
        manifest = self.home / "manifest.json"; manifest.write_bytes(b"synthetic")
        lock = self.home / "lock.json"; lock.write_bytes(b"synthetic")
        source = self.home / "source"; source.write_bytes(b"source unchanged")
        candidate = self.home / "candidate"; candidate.mkdir()
        components = {key: dict(zip(("version", "archive", "hashAlgorithm", "hash"), values))
                      for key, values in builder.ARCHIVE_PINS.items()}
        before = {p: sha(p) for p in (sdk, pg, manifest, lock, source)}
        destination, evidence = self.home / "new.zip", self.home / "evidence"
        with patch.object(builder, "collect_application", return_value=([], candidate)), \
             patch.object(builder, "collect_locks", return_value=({}, components, [], [], [])), \
             patch.object(builder, "workspace_path", return_value=source), \
             patch.object(builder, "archive_slice") as select:
            self.rejects("archive_untrusted", lambda: builder.build(manifest, builder.APPLICATION_SHA256,
                sdk, pg, lock, destination, evidence))
            select.assert_not_called()
            self.assertFalse(destination.exists())
            self.assertFalse(evidence.exists())
            destination.write_bytes(b"existing destination must survive")
            self.rejects("output_exists", lambda: builder.build(manifest, builder.APPLICATION_SHA256,
                sdk, pg, lock, destination, evidence))
            self.assertEqual(destination.read_bytes(), b"existing destination must survive")
        self.assertTrue(all(sha(p) == digest for p, digest in before.items()))

    def test_11_selected_operators_keep_adjacent_script_dependencies(self):
        selected = set(builder.OPERATORS)
        self.assertEqual(len(selected), 25)
        # This reads actual operator imports/calls, rather than repeating the allowlist.
        adjacent = re.compile(r"Join-Path\s+\$PSScriptRoot\s+['\"]([^'\"]+\.ps1)['\"]", re.I)
        for name in selected:
            text = (ROOT / "tools/windows" / name).read_text(encoding="utf-8-sig")
            for dependency in adjacent.findall(text):
                self.assertIn(dependency, selected, f"{name} requires adjacent {dependency}")

    @unittest.skipUnless(os.name == "nt", "native Windows producer")
    def test_12_unicode_transport_name_keeps_zip_and_complete_success_evidence(self):
        # Synthetic upstream seam isolates final output transport, not archive-pin validation.
        sdk = self.home / builder.ARCHIVE_PINS["dotnet"][1]
        pg = self.home / builder.ARCHIVE_PINS["postgresql"][1]
        for path in (sdk, pg):
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("fixture", b"synthetic")
        manifest = self.home / "manifest.json"; manifest.write_bytes(b"synthetic manifest")
        lock = self.home / "lock.json"; lock.write_bytes(b"synthetic lock")
        candidate = self.home / "candidate"; candidate.mkdir()
        for name in builder.OPERATORS:
            path = self.home / "tools/windows" / name
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"# synthetic operator")
        for name in builder.MANUALS:
            path = self.home / "docs" / name
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"synthetic manual")
        components = {key: dict(zip(("version", "archive", "hashAlgorithm", "hash"), values))
                      for key, values in builder.ARCHIVE_PINS.items()}
        real_hash = builder.hash_stream
        def pinned_fixture_hash(stream, algorithm="sha256"):
            if algorithm == "SHA512":
                return builder.ARCHIVE_PINS["dotnet"][3]
            if algorithm == "SHA256":
                return builder.ARCHIVE_PINS["postgresql"][3]
            return real_hash(stream, algorithm)
        for digest, name, schema, server, _frontend, size in MATRIX:
            with self.subTest(profile=name):
                destination = self.home / ("paquete Ω 漢 " + name + "-" + digest[:8] + ".zip")
                evidence = self.home / ("evidence Ω " + name + "-" + digest[:8])
                with patch.object(builder, "ROOT", self.home), \
                     patch.object(builder, "collect_application", return_value=([builder.Payload("application/manifest.json", b"synthetic")], candidate)), \
                     patch.object(builder, "collect_locks", return_value=({}, components, [], [], [])), \
                     patch.object(builder, "archive_slice", side_effect=[
                         [builder.Payload("dependencies/dotnet/dotnet.exe", b"synthetic")],
                         [builder.Payload("dependencies/postgresql/bin/postgres.exe", b"synthetic")]]), \
                     patch.object(builder, "hash_stream", side_effect=pinned_fixture_hash):
                    report = builder.build(manifest, digest, sdk, pg, lock, destination, evidence)
                self.assertTrue(report["valid"])
                self.assertEqual(report["applicationManifestSha256"], digest)
                self.assertEqual(report["slices"]["application"], {"files": server + _frontend, "bytes": size})
                self.assertEqual(report["versions"]["schema"], schema)
                self.assertEqual(report["bundleArchiveSha256"], sha(destination))
                self.assertEqual((evidence / "SHA256SUMS.txt").read_text(encoding="utf-8"),
                                 sha(destination) + "  " + destination.name + "\n")
                self.assertEqual(json.loads((evidence / "REPORT.json").read_bytes()), report)
                self.assertFalse((evidence / "FAILED.json").exists())

    def test_13_reviewed_real_applications_have_exact_separate_profiles(self):
        profiles = {
            "b7b26834ac5186792a01014b7221f4ba94940da19efafb84546ca635f868fa00":
                ("337", 6578061, "evidence/s1-20261017/treinta-tandas-308-337/CANDIDATA337.json"),
            "cf51b03c80ddec460944295daf09705f3dbdec0cd83e054f5bfc6592fb081685":
                ("397", 6653702, "evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json"),
            builder.APPLICATION_CONFIG_SHA256:
                ("532", builder.APPLICATION_PROFILES[builder.APPLICATION_CONFIG_SHA256]["bytes"],
                 "evidence/s1-20261018/sesenta-tandas-473-532/CANDIDATA532-FINAL03.json"),
            builder.APPLICATION_SHARED_SHA256:
                ("592", 6939574, "evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json")}
        # Los cuatro manifiestos históricos siguen fijados; el registro completo es exactamente la matriz actual (13 perfiles).
        self.assertTrue(set(profiles) <= set(builder.APPLICATION_PROFILES))
        self.assertEqual({row[0] for row in MATRIX}, set(builder.APPLICATION_PROFILES))
        for digest, (name, size, relative) in profiles.items():
            with self.subTest(profile=name):
                manifest = ROOT / relative
                before = sha(manifest)
                payloads, candidate = builder.collect_application(manifest, digest)
                self.assertEqual(before, digest)
                self.assertEqual(sha(manifest), before)
                server_files = 19 if name == "592" else 18
                self.assertEqual(builder.APPLICATION_PROFILES[digest], {
                    "name": name, "files": {"server": server_files, "frontend": 18}, "bytes": size})
                self.assertEqual(len(payloads), server_files + 19)  # Distributions plus exact manifest.
                self.assertEqual(sum(len(p.data) for p in payloads[1:]), size)
                self.assertEqual(candidate, ROOT / json.loads(manifest.read_bytes())["candidateDirectory"])
                self.assertTrue(all(p.path.startswith("application/") for p in payloads))

    def test_14_unreviewed_profile_and_crossed_reviewed_manifests_fail_closed(self):
        third = self.home / "third.json"
        third.write_bytes(builder.json_bytes({"schema": 9, "candidateDirectory": ".local/candidates/third",
                                              "distributions": {"server": {}, "frontend": {}}}))
        self.rejects("application_pin_mismatch", lambda: builder.collect_application(third, sha(third)))
        paths = [(ROOT / "evidence/s1-20261017/treinta-tandas-308-337/CANDIDATA337.json", builder.APPLICATION_SHA256),
                 (ROOT / "evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json", builder.APPLICATION_XLSX_SHA256),
                 (ROOT / "evidence/s1-20261018/sesenta-tandas-473-532/CANDIDATA532-FINAL03.json", builder.APPLICATION_CONFIG_SHA256),
                 (ROOT / "evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json", builder.APPLICATION_SHARED_SHA256)]
        for manifest, digest, other_digest in [(p,h,other) for p,h in paths for _,other in paths if other!=h]:
            with self.subTest(manifest=manifest.name):
                before = sha(manifest)
                self.rejects("application_manifest_untrusted", lambda: builder.collect_application(manifest, other_digest))
                self.rejects("application_pin_mismatch", lambda: builder.collect_application(manifest, digest.upper()))
                self.assertEqual(sha(manifest), before)
        self.assertFalse((self.home / "new.zip").exists())

    @unittest.skipUnless(os.name == "nt", "native Windows PowerShell 5.1 profile contract")
    def test_15_native_reader_uses_the_same_closed_profile_matrix(self):
        # Matriz completa (9–14) contra la tabla literal; el lector nativo debe coincidir fila a fila.
        module = ROOT / "tools/windows/RackClick.OfflineBundle.ps1"
        before = sha(module)
        digests = [row[0] for row in MATRIX]
        command = ". '" + str(module).replace("'", "''") + "'\n"
        command += "$rows=@();foreach($value in @('" + "','".join(digests + ["0" * 64, digests[-1].upper()]) + "')) {\n"
        command += "try {$p=Get-OfflineBundleApplicationProfile $value;$rows+=@{hash=$value;name=$p.name;server=$p.server;frontend=$p.frontend;bytes=$p.bytes;schema=(Get-OfflineBundleExpectedSchema $p);code='ok'}} "
        command += "catch {$rows+=@{hash=$value;code=[string]$_.Exception.Data['bundleCode']}}\n}\n"
        command += "$rows|ConvertTo-Json -Depth 4 -Compress"
        encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
        environment = {k: v for k, v in os.environ.items() if k.upper() != "PSMODULEPATH"}
        completed = subprocess.run([
            str(Path(os.environ["WINDIR"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"),
            "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=environment, timeout=60)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        by_hash = {row["hash"]: row for row in json.loads(completed.stdout)}
        for digest, name, schema, server, frontend, size in MATRIX:
            with self.subTest(profile=name):
                row = by_hash[digest]
                self.assertEqual(row["code"], "ok")
                self.assertEqual((row["name"], row["server"], row["frontend"], row["bytes"], row["schema"]),
                                 (name, server, frontend, size, schema))
        self.assertEqual([by_hash["0" * 64]["code"], by_hash[digests[-1].upper()]["code"]], ["application_pin_mismatch"] * 2)
        self.assertEqual(sha(module), before)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--cases", nargs="*")
    options = parser.parse_args()
    options.evidence.mkdir(exist_ok=False)
    guarded = [ROOT / "tools/package_offline_bundle.py", Path(__file__),
               ROOT / "development/toolchain.lock.json", ROOT / "development/offline-bundle.sources.json",
               ROOT / "evidence/s1-20261017/treinta-tandas-308-337/CANDIDATA337.json",
               ROOT / "evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json",
               ROOT / "tools/windows/RackClick.OfflineBundle.ps1"]
    before = {p: sha(p) for p in guarded}
    started = time.monotonic()
    with (options.evidence / "tests.log").open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.TestSuite(OfflineBundleBuilder(name) for name in options.cases) if options.cases
            else unittest.defaultTestLoader.loadTestsFromTestCase(OfflineBundleBuilder))
    unchanged = all(sha(p) == digest for p, digest in before.items())
    report = {"platform": platform.platform(), "python": platform.python_version(),
              "testsRun": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "cases": options.cases or "all",
              "seconds": round(time.monotonic() - started, 3), "guardedSourcesUnchanged": unchanged,
              "guardedSources": {p.relative_to(ROOT).as_posix(): digest for p, digest in before.items()},
              "databaseExecuted": False, "installerExecuted": False, "realPackagingExecuted": False,
              "valid": result.wasSuccessful() and unchanged}
    (options.evidence / "RESULT.json").write_bytes(builder.json_bytes(report))
    print(json.dumps(report))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
