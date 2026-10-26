"""C1 native PostgreSQL/log checks on an identified, isolated pre-M3 build.

Raw logs, generated credentials and binlogs stay in ignored .local directories.
The optional negative control must FAIL: it contaminates an owned log copy.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import sys
import unittest
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[3]


def secret_present(log: bytes, values: list[str]) -> bool:
    for value in values:
        if not value:
            continue
        variants = {value, quote(value, safe=""), json.dumps(value)[1:-1]}
        if any(text.encode(encoding) in log for text in variants
               for encoding in ("utf-8", "utf-16-le")):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--mode", choices=("all", "logs", "negative-control"), default="all")
    args = parser.parse_args()
    baseline_path = args.baseline.resolve()
    private = (ROOT / ".local").resolve()
    if not baseline_path.is_relative_to(private):
        raise ValueError("Baseline must be an owned .local snapshot")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
    work = baseline_path.parent
    source = work / "source"
    dll = work / "app/RackClick.Server.dll"
    if (baseline["workspace"] != str(work) or baseline["source"] != str(source)
            or not work.name.startswith("c1-logs-") or not dll.is_file()):
        raise ValueError("Invalid baseline binding")
    tests = source / "development/server/tests"
    sys.path.insert(0, str(tests))
    import pg_support as pg
    pg.WORKSPACE = ROOT
    pg.SERVER_ROOT = source / "development/server"
    pg.DEFAULT_DLL = dll
    from test_admin_user_password import UserPasswordPostgres
    from test_admin_user_state import UserStatePostgres
    from test_admin_members import MemberPostgres
    from test_admin_effective_permissions import EffectivePermissionsPostgres

    class LogSecretPostgres(UserPasswordPostgres):
        inject_leak = args.mode == "negative-control"

        def markers(self, *clients):
            values = [self.password, self.db.owner_password, self.db.runtime_password,
                      self.lab.admin_password, self.db.connection(self.lab.port)]
            for client in clients:
                if client.cookie:
                    values.extend([client.cookie, client.cookie.split("=", 1)[-1]])
                if client.csrf:
                    values.append(client.csrf)
            hashes = self.lab.sql(self.db, "SELECT password_hash FROM app_user; "
                                  "SELECT token_hash,csrf_hash FROM app_session")
            values.extend(hashes.replace("|", "\n").splitlines())
            return values

        def check_log(self, values, *, expect_error=False):
            self.server.close()  # flush stdout AND stderr before scanning their capture
            data = self.server.log_path.read_bytes()
            self.assertGreater(len(data), 0, "Log capture must not be empty")
            self.assertIn(b"Now listening", data, "Actual server logging must be active")
            if expect_error:
                self.assertIn(b"PostgresException", data, "Database error must reach logger")
            self.assertFalse(secret_present(data, values),
                             "Server log contains a synthetic secret; raw evidence stays private")

        def test_logs_login_reset_and_revoked_session(self):
            self.initialize()
            user, old = self.add_user("c1-log-target")
            values = self.markers(self.admin, old)
            new_password = "c1-synthetic-reset-" + secrets.token_urlsafe(24)
            values.append(new_password)
            self.expect(self.reset(user, new_password), 200)
            self.expect(old.request("GET", "/api/v1/me"), 401)
            self.expect(pg.Client(self.server).login("c1-log-target", self.password), 401)
            fresh = pg.Client(self.server)
            self.expect(fresh.login("c1-log-target", new_password), 200)
            values.extend(self.markers(self.admin, fresh))
            self.server.close()
            if self.inject_leak:
                # Controlled contamination, not an assertion that product leaked.
                with self.server.log_path.open("ab") as stream:
                    stream.write(new_password.encode("utf-8"))
            self.check_log(values)

        def test_logs_failed_audit_preserves_sessions_without_exception_secrets(self):
            self.initialize()
            user, target = self.add_user("c1-log-rollback")
            values = self.markers(self.admin, target)
            sql_marker = "c1-synthetic-sql-" + secrets.token_hex(20)
            new_password = "c1-synthetic-rejected-" + secrets.token_urlsafe(24)
            values.extend([sql_marker, new_password])
            self.lab.sql(self.db, "CREATE FUNCTION c1_log_reject() RETURNS trigger "
                         "LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='user.password.reset' "
                         f"THEN RAISE EXCEPTION {pg.literal(sql_marker)}; END IF; RETURN NEW; END $$; "
                         "CREATE TRIGGER c1_log_reject BEFORE INSERT ON audit_event "
                         "FOR EACH ROW EXECUTE FUNCTION c1_log_reject();")
            before = self.snapshot()
            self.expect(self.reset(user, new_password), 503)
            self.assertEqual(before, self.snapshot(), "Audit failure must roll back durable changes")
            self.expect(target.request("GET", "/api/v1/me"), 200)
            self.check_log(values, expect_error=True)

        def test_logs_rejected_database_password_does_not_expose_connection(self):
            self.initialize()
            self.server.close()
            bad_password = "c1-synthetic-db-" + secrets.token_urlsafe(24)
            bad = replace(self.db, runtime_password=bad_password)
            self.server = self.lab.start_server(bad)
            supplied = "c1-synthetic-login-" + secrets.token_urlsafe(24)
            self.expect(pg.Client(self.server).login("qa-admin", supplied), 503)
            self.check_log([bad_password, supplied, bad.connection(self.lab.port)], expect_error=True)

    class ScannerControl(unittest.TestCase):
        def test_scanner_detects_both_streams_and_escaped_values(self):
            marker = "c1-fixture/only+not-a-real-secret"
            for value in (marker, quote(marker, safe=""), json.dumps(marker)[1:-1]):
                for encoding in ("utf-8", "utf-16-le"):
                    self.assertTrue(secret_present(value.encode(encoding), [marker]))
            self.assertFalse(secret_present(b"ordinary diagnostic", [marker]))

    class SafeResult(unittest.TextTestResult):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.records = []

        def addSuccess(self, test):
            super().addSuccess(test)
            self.records.append({"name": test.id(), "outcome": "passed"})

        def addFailure(self, test, err):
            super().addFailure(test, err)
            self.records.append({"name": test.id(), "outcome": "failed"})

        def addError(self, test, err):
            super().addError(test, err)
            self.records.append({"name": test.id(), "outcome": "error",
                                 "exceptionType": err[0].__name__})

    evidence = args.evidence.resolve()
    if not evidence.is_relative_to(private):
        raise ValueError("Raw C1 output must remain under .local")
    evidence.mkdir(parents=True, exist_ok=False)
    pg.protect_directory(evidence)
    inputs = [p for p in source.rglob("*") if p.is_file() and
              not any(part in ("bin", "obj") for part in p.relative_to(source).parts)]
    inputs.append(Path(__file__).resolve())
    frozen_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    dll_hash = hashlib.sha256(dll.read_bytes()).hexdigest()
    lab = pg.Lab("c1-log-secrets")
    report = {"schemaVersion": 1, "platform": platform.platform(),
              "sourceCommit": baseline["sourceCommit"], "dllSha256": dll_hash,
              "sourceArchiveSha256": baseline["sourceArchiveSha256"], "mode": args.mode,
              "testSourceSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "newCluster": True, "postgresql": "17.11", "host": "127.0.0.1",
              "qaTouched": False, "mfaAcceptance": False}
    try:
        with lab, (evidence / "tests-private.log").open("w", encoding="utf-8") as stream:
            report["actualPostgresqlVersion"] = lab.sql("postgres", "SHOW server_version", admin=True)
            for cls in (LogSecretPostgres, MemberPostgres, UserStatePostgres,
                        EffectivePermissionsPostgres, UserPasswordPostgres):
                cls.lab = lab
            if args.mode == "negative-control":
                selected = [LogSecretPostgres("test_logs_login_reset_and_revoked_session")]
            else:
                selected = [ScannerControl("test_scanner_detects_both_streams_and_escaped_values")]
                selected += [LogSecretPostgres(name) for name in (
                    "test_logs_login_reset_and_revoked_session",
                    "test_logs_failed_audit_preserves_sessions_without_exception_secrets",
                    "test_logs_rejected_database_password_does_not_expose_connection")]
                if args.mode == "all":
                    selected += [
                        MemberPostgres("test_members_commit_immediate_replay_and_noop"),
                        EffectivePermissionsPostgres("test_effective_composition_matches_me"),
                        UserStatePostgres("test_state_last_active_global_admin_and_self_disable"),
                        UserStatePostgres("test_state_sessions_reactivation_noop_and_replay"),
                        UserPasswordPostgres("test_password_sessions_persistence_lockout_inactive_and_replay"),
                        UserPasswordPostgres("test_password_audit_rollback_exact_concurrency_login_and_cancel"),
                    ]
            result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=SafeResult).run(
                unittest.TestSuite(selected))
            report.update(testsRun=result.testsRun, cases=result.records,
                          successful=result.wasSuccessful())
    finally:
        lab.close()
        report["labStopped"] = not lab.running
        report["inputsUnchanged"] = all(hashlib.sha256(p.read_bytes()).hexdigest() == sha
                                        for name, sha in frozen_hashes.items() for p in (Path(name),))
        report["dllUnchanged"] = hashlib.sha256(dll.read_bytes()).hexdigest() == dll_hash
        (evidence / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if all(report.get(key) for key in
                    ("successful", "labStopped", "inputsUnchanged", "dllUnchanged")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
