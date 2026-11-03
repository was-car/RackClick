"""Reject drift between the trusted payload bundle and the CRT extraction branch.

This branch matters on a clean server, even when the build host already has CRT.
No executable is installed by this test.
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import package_server_installer as producer


class InstallerPrerequisitePinTests(unittest.TestCase):
    def test_crt_extraction_uses_the_bundle_accepted_by_setup(self):
        folder = ROOT / 'tools/windows/server-install'
        setup = (folder / 'RackClick.Setup.ps1').read_text(encoding='utf-8-sig')
        crt = (folder / 'RackClick.Setup.Prerequisite.ps1').read_text(encoding='utf-8-sig')
        expected = re.findall(r"manifest\.bundleArchiveSha256-cne'([0-9a-f]{64})'", setup)
        actual = re.findall(r"\$actual -cne '([0-9a-f]{64})'", crt)
        self.assertEqual(len(expected), 1)
        self.assertEqual(actual, expected, 'CRT extraction is bound to another bundle')

    def test_service_preparation_uses_the_same_pin_for_verification_and_child(self):
        folder = ROOT / 'tools/windows/server-install'
        setup = (folder / 'RackClick.Setup.ps1').read_text(encoding='utf-8-sig')
        prepare = (folder / 'Prepare-RackClickServer.ps1').read_text(encoding='utf-8-sig')
        expected = re.findall(r"manifest\.bundleArchiveSha256-cne'([0-9a-f]{64})'", setup)
        verify = re.findall(r"Hash\.ToLowerInvariant\(\) -cne '([0-9a-f]{64})'", prepare)
        child = re.findall(r"'-ExpectedArchiveSha256','([0-9a-f]{64})'", prepare)
        self.assertEqual(verify, expected)
        self.assertEqual(child, expected)

    def test_actual_sources_pass_the_build_guard(self):
        setup = (ROOT / 'tools/windows/server-install/RackClick.Setup.ps1').read_text(encoding='utf-8-sig')
        expected, = re.findall(r"manifest\.bundleArchiveSha256-cne'([0-9a-f]{64})'", setup)
        self.assertEqual(producer.checked_edition('13', expected), '13')


class NativePinBuildGuardTests(unittest.TestCase):
    PIN = '1' * 64
    OTHER = '2' * 64

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='native-pin-', dir=ROOT / '.local')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'tools/windows/server-install'
        self.folder.mkdir(parents=True)
        self.write_sources(self.PIN, self.PIN, self.PIN)

    def write_sources(self, crt, prepare, child):
        (self.folder / 'RackClick.Setup.ps1').write_text(
            "if($manifest.bundleArchiveSha256-cne'" + self.PIN + "'){throw 'pin'}", encoding='utf-8')
        (self.folder / 'RackClick.Setup.Prerequisite.ps1').write_text(
            "if($actual -cne '" + crt + "'){throw 'pin'}", encoding='utf-8')
        (self.folder / 'Prepare-RackClickServer.ps1').write_text(
            "if((Get-FileHash $archive).Hash.ToLowerInvariant() -cne '" + prepare + "'){throw 'pin'}\n"
            "$args=@('-ExpectedArchiveSha256','" + child + "')", encoding='utf-8')

    def check(self):
        with patch.object(producer, 'ROOT', self.root):
            return producer.checked_edition('13', self.PIN)

    def test_coherent_control(self):
        self.assertEqual(self.check(), '13')

    def test_old_crt_pin_rejected(self):
        self.write_sources(self.OTHER, self.PIN, self.PIN)
        with self.assertRaisesRegex(ValueError, '^native_bundle_pins_incoherent$'):
            self.check()

    def test_old_prepare_verifier_pin_rejected(self):
        self.write_sources(self.PIN, self.OTHER, self.PIN)
        with self.assertRaisesRegex(ValueError, '^native_bundle_pins_incoherent$'):
            self.check()

    def test_old_prepare_child_pin_rejected(self):
        self.write_sources(self.PIN, self.PIN, self.OTHER)
        with self.assertRaisesRegex(ValueError, '^native_bundle_pins_incoherent$'):
            self.check()

    def test_missing_pin_is_rejected(self):
        (self.folder / 'RackClick.Setup.Prerequisite.ps1').write_text('# missing', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '^native_bundle_pins_incoherent$'):
            self.check()

    def test_duplicate_native_pin_is_rejected(self):
        path = self.folder / 'RackClick.Setup.Prerequisite.ps1'
        path.write_text(path.read_text(encoding='utf-8') * 2, encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '^native_bundle_pins_incoherent$'):
            self.check()

    def test_build_rejects_before_any_input_or_output(self):
        self.write_sources(self.OTHER, self.PIN, self.PIN)
        output = self.root / 'must-not-exist.zip'
        before = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*'))
        with patch.object(producer, 'ROOT', self.root):
            with self.assertRaisesRegex(ValueError, '^native_bundle_pins_incoherent$'):
                producer.build(self.root / 'missing.zip', self.root / 'missing-publish', output,
                               bundle_sha256=self.PIN, edition='13')
        self.assertFalse(output.exists())
        self.assertEqual(before, sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*')))

    def test_candidate_only_in_setup_comment_does_not_authorize_other_pin(self):
        path = self.folder / 'RackClick.Setup.ps1'
        path.write_text("# candidate '" + self.PIN + "'\nif($manifest.bundleArchiveSha256-cne'" +
                        self.OTHER + "'){throw 'pin'}", encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '^edition_source_pin_mismatch$'):
            self.check()

    def test_setup_comparison_only_in_comment_is_not_a_guard(self):
        path = self.folder / 'RackClick.Setup.ps1'
        path.write_text("# if($manifest.bundleArchiveSha256-cne'" + self.PIN + "'){throw 'pin'}", encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '^edition_source_pin_mismatch$'):
            self.check()

    def test_native_controls_only_in_comments_are_not_guards(self):
        for filename, line_index in [('RackClick.Setup.Prerequisite.ps1', 0),
                                     ('Prepare-RackClickServer.ps1', 0),
                                     ('Prepare-RackClickServer.ps1', 1)]:
            with self.subTest(file=filename, line=line_index):
                self.write_sources(self.PIN, self.PIN, self.PIN)
                path = self.folder / filename
                lines = path.read_text(encoding='utf-8').splitlines(True)
                lines[line_index] = '# ' + lines[line_index]
                path.write_text(''.join(lines), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, '^native_bundle_pins_incoherent$'):
                    self.check()


if __name__ == '__main__':
    unittest.main()
