"""Coordinator of the personal RC9 port-type palette block; no real QA mutation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-910-969'
GIT = ROOT / '.local/git-2.55.0.5/cmd/git.exe'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def init():
    E.mkdir(parents=True, exist_ok=True)
    guards = {}
    paths = [ROOT / '.local/qa-rc9/current.json', ROOT / '.local/qa-wascar/current.json',
             ROOT / 'development/server/global.json', ROOT / 'development/toolchain.lock.json',
             ROOT / 'development/frontend/package-lock.json']
    # Private contents are never copied to evidence: only path/digest metadata.
    for pointer in paths[:2]:
        directory = Path(json.loads(pointer.read_bytes())['directory'])
        paths.extend(p for p in directory.iterdir() if p.is_file())
    old = ROOT / 'evidence/s1-20261018/sesenta-tandas-850-909'
    paths.extend(p for p in old.rglob('*') if p.is_file())
    paths.extend(p for p in (ROOT / 'development/server/database').glob('*.sql') if p.name[:3].isdigit() and int(p.name[:3]) <= 11)
    paths.extend(p for p in (ROOT / 'tools/windows').glob('*') if p.is_file())
    paths.extend(p for p in (ROOT / 'development/frontend/rc9-reference').rglob('*') if p.is_file())
    mpath = ROOT / 'evidence/s1-20261018/tanda-849/CANDIDATA849.json'
    m = json.loads(mpath.read_bytes())
    paths += [mpath] + [ROOT / m['candidateDirectory'] / part / p for part, files in m['distributions'].items() for p in files]
    for p in sorted(set(paths)):
        guards[p.relative_to(ROOT).as_posix()] = sha(p)
    base = subprocess.check_output([str(GIT), 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    write(E / 'INICIO.json', dict(utc=datetime.now(timezone.utc).isoformat(), baseCommit=base,
         guards=guards, realQaAccessed=False, applicationBuildsPlanned=1, frontendBuildsPlanned=1,
         progress=78, scope='Personal type palette only; QA849/package909 remain unchanged.'))
    print(json.dumps(dict(base=base, protectedFiles=len(guards), progress=78)))


def build(attempt):
    out = E / ('BUILD-' + attempt + '.json')
    if out.exists():
        raise RuntimeError('Preserve original attempt evidence')
    lock = json.loads((ROOT / 'development/toolchain.lock.json').read_bytes())
    tools = {c['id']: ROOT / '.local' / c['installDirectory'] / c['executable'] for c in lock['components']}
    candidate = ROOT / '.local/candidates' / ('port-colors969-' + attempt + '-' + uuid.uuid4().hex)
    candidate.mkdir(parents=True, exist_ok=False)
    server = candidate / 'server'
    frontend = candidate / 'frontend'
    tracked = subprocess.check_output([str(GIT), 'ls-files', 'development/server/src', 'development/frontend/src',
               'development/frontend/build.mjs', 'development/server/database'], cwd=ROOT, text=True).splitlines()
    additional = [p.relative_to(ROOT).as_posix() for folder, pattern in [('development/server/src', '*.cs'),
                 ('development/server/database', '*.sql'), ('development/frontend/src', '*')]
                 for p in (ROOT / folder).rglob(pattern) if p.is_file() and not {'bin','obj'} & set(p.parts)]
    files = sorted(set(tracked + additional))
    frozen = {p: sha(ROOT / p) for p in files}
    write(E / ('SOURCE-FREEZE-' + attempt + '.json'), dict(sources=frozen))
    record = dict(utc=datetime.now(timezone.utc).isoformat(), attempt=attempt, successful=False,
                  candidateDirectory=candidate.relative_to(ROOT).as_posix(), commands=[])
    jobs = [([str(tools['dotnet']), 'publish', 'src/RackClick.Server/RackClick.Server.csproj',
              '-c', 'Release', '--no-restore', '-o', str(server), '-p:UseAppHost=false'], ROOT / 'development/server', 'server'),
            ([str(tools['node']), 'build.mjs'], ROOT / 'development/frontend', 'frontend')]
    try:
        for command, cwd, name in jobs:
            started = time.monotonic()
            with (E / ('BUILD-' + attempt + '-' + name + '.log')).open('xb') as log:
                done = subprocess.run(command, cwd=cwd, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
            record['commands'].append(dict(command=command, exitCode=done.returncode, seconds=round(time.monotonic()-started,3)))
            if done.returncode:
                raise RuntimeError(name + ' build failed; preserve log')
        shutil.copytree(ROOT / 'development/frontend/dist', frontend)
        assert all(sha(ROOT / p) == h for p, h in frozen.items()), 'Source changed during build'
        distributions = dict(server=tree(server), frontend=tree(frontend))
        previous = json.loads((ROOT / 'evidence/s1-20261018/tanda-849/CANDIDATA849.json').read_bytes())
        for p, h in previous['distributions']['frontend'].items():
            if p != 'app.js':
                assert distributions['frontend'][p] == h, p
        for p, h in previous['distributions']['server'].items():
            if p.startswith('database/') or p in ['Npgsql.dll','RackClick.Server.deps.json','RackClick.Server.runtimeconfig.json']:
                assert distributions['server'][p] == h, p
        manifest = dict(utc=datetime.now(timezone.utc).isoformat(), schema=12,
            candidateDirectory=candidate.relative_to(ROOT).as_posix(), serverDll=(server/'RackClick.Server.dll').relative_to(ROOT).as_posix(),
            frontend=frontend.relative_to(ROOT).as_posix(), distributions=distributions,
            fileCount=sum(map(len, distributions.values())), sourcesFreeze=('SOURCE-FREEZE-' + attempt + '.json'),
            selectedInRealQa=False, windowsPackageSupported=False)
        write(E / ('CANDIDATA969-' + attempt + '.json'), manifest)
        record.update(successful=True, sourcesUnchanged=True, schema=12, candidateFileCount=manifest['fileCount'])
    finally:
        write(out, record)
    print(json.dumps(record))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init','build'])
    parser.add_argument('--attempt', default='01')
    args = parser.parse_args()
    init() if args.action == 'init' else build(args.attempt)
