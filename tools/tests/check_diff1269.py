"""Retain the complete whitespace check and only raw evidence patch exceptions."""
import base64,json,re,subprocess
from seal_integration1269 import ROOT,E,GIT,sha,stage
def record(r):return dict(exitCode=r.returncode,stdoutBase64=base64.b64encode(r.stdout).decode(),stderrBase64=base64.b64encode(r.stderr).decode())
def main():
 names=['DIFF-CHECK-FULL.json','DIFF-CHECK-RAW.json','DIFF-CHECK-ALCANCE.json'];assert not any((E/n).exists() for n in names);stage();raw=subprocess.run([str(GIT),'diff','--cached','--check'],cwd=ROOT,capture_output=True);assert not raw.stderr;excluded={};locations=[]
 if raw.returncode:
  assert raw.returncode==2
  for line in raw.stdout.decode().splitlines():
   if line.startswith('+'):continue
   m=re.fullmatch(r'(.+\.patch):(\d+): (trailing whitespace\.|new blank line at EOF\.)',line);assert m,line;path,num,reason=m.groups();assert path.startswith(E.relative_to(ROOT).as_posix()+'/');excluded[path]=sha(ROOT/path);locations.append(dict(path=path,line=int(num),finding=reason))
  assert excluded
 filtered=subprocess.run([str(GIT),'diff','--cached','--check','--','.']+[':(exclude)'+p for p in excluded],cwd=ROOT,capture_output=True);assert filtered.returncode==0 and not filtered.stdout and not filtered.stderr
 scope=dict(excludedArtifacts=excluded,exactFindings=locations,productCodeExcluded=False,codeAndDocsClean=True,evidenceBytesModified=False,reason='Preserve raw patch context only; never exclude product/code/docs.',finalSealAlsoExcludesItsGeneratedPatch=E.relative_to(ROOT).as_posix()+'/CAMBIOS.patch')
 for n,data in zip(names,[record(raw),record(filtered),scope]):
  with (E/n).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')
 print(json.dumps(dict(fullExit=raw.returncode,filteredExit=filtered.returncode,excludedArtifacts=excluded,codeAndDocsClean=True)))
if __name__=='__main__':main()
