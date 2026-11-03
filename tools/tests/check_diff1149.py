"""Store the full whitespace result; preserve only exact raw evidence patch exceptions."""
import base64
import argparse
import json
import re
import subprocess

from seal_integration1149 import ROOT,E,GIT,sha,public_paths

def record(result):return dict(exitCode=result.returncode,stdoutBase64=base64.b64encode(result.stdout).decode(),stderrBase64=base64.b64encode(result.stderr).decode())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',choices=['01','02'],default='01');args=parser.parse_args()
    suffix='' if args.attempt=='01' else '-'+args.attempt
    names=['DIFF-CHECK-FULL'+suffix+'.json','DIFF-CHECK-RAW'+suffix+'.json','DIFF-CHECK-ALCANCE'+suffix+'.json']
    assert not any((E/n).exists() for n in names)
    subprocess.run([str(GIT),'add','--',*public_paths()],cwd=ROOT,check=True,capture_output=True)
    raw=subprocess.run([str(GIT),'diff','--cached','--check'],cwd=ROOT,capture_output=True)
    assert not raw.stderr
    excluded={};locations=[]
    if raw.returncode:
        assert raw.returncode==2
        for line in raw.stdout.decode().splitlines():
            if line.startswith('+'):continue
            match=re.fullmatch(r'(.+\.patch):(\d+): (trailing whitespace\.|new blank line at EOF\.)',line)
            assert match,line
            name,number,reason=match.groups();assert name.startswith(E.relative_to(ROOT).as_posix()+'/'),line
            excluded[name]=sha(ROOT/name);locations.append(dict(path=name,line=int(number),finding=reason))
        assert excluded
    filtered=subprocess.run([str(GIT),'diff','--cached','--check','--','.']+[':(exclude)'+p for p in excluded],cwd=ROOT,capture_output=True)
    assert filtered.returncode==0 and not filtered.stdout and not filtered.stderr
    scope=dict(excludedArtifacts=excluded,exactFindings=locations,productCodeExcluded=False,codeAndDocsClean=True,
        evidenceBytesModified=False,reason='Preserve raw patch context, if any; all product/code/docs checked without exclusion.',
        finalSealAlsoExcludesItsGeneratedPatch=E.relative_to(ROOT).as_posix()+'/CAMBIOS.patch')
    for name,data in zip(names,[record(raw),record(filtered),scope]):
        with (E/name).open('x',encoding='utf-8') as stream:stream.write(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(fullExit=raw.returncode,filteredExit=filtered.returncode,excludedArtifacts=excluded,codeAndDocsClean=True)))

if __name__=='__main__':main()
