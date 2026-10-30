"""Seal the staged non-evidence diff and all new evidence, preserving prior seals."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-473-532'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    for name in ['revision/ADDENDUM-FINAL.md', 'revision/METADATOS-FINALES.json', 'revision/SEAL-REVISION-FINAL.json']:
        assert (E / name).is_file(), name
    for name in ['CAMBIOS.patch', 'SHA256SUMS']:
        if (E / name).exists():
            raise SystemExit('Preserve existing final diff/seal; do not overwrite')
    git = str(ROOT / '.local/git-2.55.0.5/cmd/git.exe')
    patch = subprocess.check_output([git, 'diff', '--cached', '--binary', '--', '.',
        ':(exclude)evidence/s1-20261018/sesenta-tandas-473-532'], cwd=ROOT)
    assert patch and b'PrivateTemplateConfigurations.cs' in patch and b'PLAN-SESENTA-TANDAS-473-532.json' in patch
    (E / 'CAMBIOS.patch').write_bytes(patch)
    files = sorted((p for p in E.rglob('*') if p.is_file()), key=lambda p: p.relative_to(E).as_posix())
    lines = [sha(p) + '  ' + p.relative_to(E).as_posix() for p in files]
    (E / 'SHA256SUMS').write_bytes(('\n'.join(lines) + '\n').encode('utf-8'))
    assert all(sha(E / line.split('  ', 1)[1]) == line.split('  ', 1)[0] for line in lines)
    print(json.dumps(dict(evidenceFiles=len(files), patchBytes=len(patch),
                         sha256Sums=sha(E / 'SHA256SUMS'), published=False, privateInputsPackaged=False)))


if __name__ == '__main__':
    main()
