"""Seal the reviewed Windows/QA12 block and stage only its public local changes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from verify_integration1029 import protected_inputs, current_product, technical_gate

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-970-1029'
GIT = ROOT / '.local/git-2.55.0.5/cmd/git.exe'
EXCLUDED_DIFFS = [E.relative_to(ROOT).as_posix() + '/qa-copy/DELTA-FOCO03.patch',
                  E.relative_to(ROOT).as_posix() + '/CAMBIOS.patch']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git(*args):
    return subprocess.check_output([str(GIT), *args], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-sha256', required=True)
    args = parser.parse_args()
    review = E / 'revision/CIERRE-REVISADO.json'
    assert sha(review) == args.review_sha256
    approved = json.loads(review.read_bytes())
    assert approved['approved'] and approved['progress'] == 78 and not approved['finalAdoption']
    assert all(sha(ROOT / p) == h for p, h in approved['files'].items())
    assert json.loads((E / 'VERIFICACION-FINAL.json').read_bytes())['successful']
    protected_inputs()
    current_product()
    technical_gate()
    paths = [p for p in git('ls-files', '-m', '-o', '--exclude-standard', '-z').decode().split('\0') if p]
    prefixes = ['docs/', 'development/server/tests/', 'tools/tests/', 'tools/windows/',
                E.relative_to(ROOT).as_posix() + '/']
    exact = ['CHANGELOG.md', 'GUIA-QA-WASCAR.html', 'GUIA-QA-RESTAURADO.html',
             'development/server/README.md', 'development/frontend/README.md',
             'development/server/src/RackClick.Server/RecoveryAdministrator.cs',
             'tools/package_offline_bundle.py']
    assert paths and all(p in exact or any(p.startswith(prefix) for prefix in prefixes) for p in paths)
    git('add', '--', *paths)
    check_args = ['diff', '--cached', '--check', '--', '.'] + [':(exclude)' + p for p in EXCLUDED_DIFFS]
    subprocess.run([str(GIT), *check_args], cwd=ROOT, check=True, capture_output=True)
    patch = E / 'CAMBIOS.patch'
    with patch.open('xb') as stream:
        stream.write(git('diff', '--cached', '--binary', '--', '.', ':(exclude)evidence/**'))
    entries = [(sha(p), p.relative_to(E).as_posix()) for p in sorted(E.rglob('*'))
               if p.is_file() and p.name != 'SHA256SUMS']
    manifest = E / 'SHA256SUMS'
    with manifest.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(''.join(h + '  ' + p + '\n' for h, p in entries))
    git('add', '--', str(E.relative_to(ROOT)))
    subprocess.run([str(GIT), *check_args],
                   cwd=ROOT, check=True, capture_output=True)
    print(json.dumps(dict(evidenceFiles=len(entries), manifestSha256=sha(manifest),
                          publicDiffBytes=patch.stat().st_size, published=False)))


if __name__ == '__main__':
    main()
