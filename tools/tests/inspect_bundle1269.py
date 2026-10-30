"""Run the public Windows integrity reader on finalZIP02, without installation."""
import json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269'
def main():
 out=E/'ZIP02-CLI.json';assert not out.exists();package=json.loads((E/'PACKAGES-02.json').read_bytes());p=package['outputs'][0]
 command=[str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoLogo','-NoProfile','-NonInteractive','-File',str(ROOT/'tools/windows/Test-RackClickOfflineBundle.ps1'),'-ArchivePath',str(ROOT/p['path']),'-ExpectedArchiveSha256',p['sha256']]
 start=time.monotonic();r=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=180);report=json.loads(r.stdout)
 (E/'ZIP02-CLI.stdout').write_bytes(r.stdout);(E/'ZIP02-CLI.stderr').write_bytes(r.stderr)
 valid=r.returncode==0 and not r.stderr and report['valid'] and report['code']=='bundle_verified' and report['bundleArchiveSha256']==p['sha256'] and report['versions']['schema']==13
 data=dict(successful=valid,command=command,exitCode=r.returncode,seconds=round(time.monotonic()-start,3),report=report,newInstallation=False,newRestore=False)
 with out.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')
 print(json.dumps(data));return 0 if valid else 1
if __name__=='__main__':raise SystemExit(main())
