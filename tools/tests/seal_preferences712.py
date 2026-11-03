"""Seal public staged changes and new evidence once the independent closure passes."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ER = 'evidence/s1-20261018/sesenta-tandas-653-712'
E = ROOT / ER
GIT = str(ROOT / '.local/git-2.55.0.5/cmd/git.exe')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    for name in ['CAMBIOS.patch', 'SHA256SUMS']:
        if (E / name).exists():
            raise SystemExit('Preserve previous evidence seal')
    assert json.loads((E / 'VERIFICACION-FINAL.json').read_bytes())['successful']
    closing = json.loads((E / 'revision/METADATOS-CIERRE.json').read_bytes())
    assert closing['valid'] and (E / 'revision/ADENDA-CIERRE.md').is_file()
    assert all(sha(E / p) == h for p, h in closing['observedFilesSha256'].items())
    assert all(sha(ROOT / p) == h for p, h in closing['continuityDocumentsSha256'].items())
    assert all(sha(ROOT / p) == details['sha256'] for p, details in closing['guides'].items())
    assert sha(E / 'revision/SEAL-REVISION.json') == '385bf3b486d32ebd14fac91fc3df48e5aedbb4b04ae6f8549e52789f21e4ea3d'
    changed = subprocess.check_output([GIT, 'ls-files', '-m', '-o', '--exclude-standard', '-z'], cwd=ROOT)
    paths = [p.decode('utf-8') for p in changed.split(b'\0') if p]
    allowed = ('development/', 'docs/', ER + '/', 'tools/tests/', 'tools/windows/qa_guide.py')
    assert all(p.startswith(allowed) or p in ['CHANGELOG.md', 'GUIA-QA-WASCAR.html', 'GUIA-QA-RESTAURADO.html'] for p in paths)
    if paths:
        subprocess.run([GIT, 'add', '--', *paths], cwd=ROOT, check=True)
    subprocess.run([GIT, 'diff', '--cached', '--check'], cwd=ROOT, check=True)
    patch = subprocess.check_output([GIT, 'diff', '--cached', '--binary', '--', '.', ':(exclude)' + ER + '/**'], cwd=ROOT)
    assert patch and b'diff --git' in patch
    with (E / 'CAMBIOS.patch').open('xb') as stream:
        stream.write(patch)
    files = sorted(p for p in E.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
    lines = [sha(p) + '  ' + p.relative_to(E).as_posix() for p in files]
    with (E / 'SHA256SUMS').open('xb') as stream:
        stream.write(('\n'.join(lines) + '\n').encode('utf-8'))
    subprocess.run([GIT, 'add', '--', ER], cwd=ROOT, check=True)
    # Patch contains exact original diff context; do not rewrite its raw whitespace.
    subprocess.run([GIT, 'diff', '--cached', '--check', '--', '.', ':(exclude)' + ER + '/CAMBIOS.patch'], cwd=ROOT, check=True)
    print(json.dumps(dict(files=len(files), sha256Sums=sha(E / 'SHA256SUMS'),
                          publicDiffBytes=len(patch), published=False)))


if __name__ == '__main__':
    main()
