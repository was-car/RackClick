"""Keep the raw whitespace finding in a stored patch, then check all other changes."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

from seal_integration1029 import ROOT, E, GIT


def record(result):
    return dict(exitCode=result.returncode, stdoutBase64=base64.b64encode(result.stdout).decode(),
                stderrBase64=base64.b64encode(result.stderr).decode())


def main():
    names = ['DIFF-CHECK-FULL.json', 'DIFF-CHECK-RAW.json', 'DIFF-CHECK-ALCANCE.json']
    assert not any((E / name).exists() for name in names)
    paths = subprocess.check_output([str(GIT), 'ls-files', '-m', '-o', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    paths = [p for p in paths if p]
    prefixes = ['docs/', 'development/server/tests/', 'tools/tests/', 'tools/windows/',
                E.relative_to(ROOT).as_posix() + '/']
    exact = ['CHANGELOG.md', 'GUIA-QA-WASCAR.html', 'GUIA-QA-RESTAURADO.html',
             'development/server/README.md', 'development/frontend/README.md',
             'development/server/src/RackClick.Server/RecoveryAdministrator.cs',
             'tools/package_offline_bundle.py']
    assert paths and all(p in exact or any(p.startswith(prefix) for prefix in prefixes) for p in paths)
    subprocess.run([str(GIT), 'add', '--', *paths], cwd=ROOT, check=True, capture_output=True)
    raw = subprocess.run([str(GIT), 'diff', '--cached', '--check'], cwd=ROOT, capture_output=True)
    artifact = E.relative_to(ROOT).as_posix() + '/qa-copy/DELTA-FOCO03.patch'
    assert raw.returncode != 0 and not raw.stderr
    lines = raw.stdout.decode().splitlines()
    assert lines == [artifact + ':17: trailing whitespace.', '+ ',
                     artifact + ':18: trailing whitespace.', '+ '], lines
    filtered = subprocess.run([str(GIT), 'diff', '--cached', '--check', '--', '.', ':(exclude)' + artifact],
                              cwd=ROOT, capture_output=True)
    assert filtered.returncode == 0 and not filtered.stdout and not filtered.stderr
    scope = dict(excludedArtifact=artifact, excludedLines=[17, 18], productCodeExcluded=False,
                 excludedEvidencePatch=artifact, excludedEvidencePatchSha256=hashlib.sha256((ROOT / artifact).read_bytes()).hexdigest(),
                 fullCheckRecord='DIFF-CHECK-FULL.json', filteredCheckRecord='DIFF-CHECK-RAW.json',
                 evidenceBytesModified=False, reason='Stored diff context contains +space lines; preserve exact evidence bytes.',
                 finalSealAlsoExcludesItsGeneratedPatch=E.relative_to(ROOT).as_posix() + '/CAMBIOS.patch')
    for name, value in zip(names, [record(raw), record(filtered), scope]):
        with (E / name).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(value, indent=2) + '\n')
    print(json.dumps(dict(fullExit=raw.returncode, filteredExit=0, exactExcludedArtifact=artifact,
                          preservedContextLines=2, codeAndDocsClean=True)))


if __name__ == '__main__':
    main()
