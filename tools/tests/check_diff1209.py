"""Preserve the complete whitespace check, with no artifact exceptions."""
import base64
import json
import subprocess
from seal_onboarding1209 import ROOT,E,GIT,public_paths

def main():
    out=E/'DIFF-CHECK.json';assert not out.exists()
    subprocess.run([str(GIT),'add','--',*public_paths()],cwd=ROOT,check=True,capture_output=True)
    result=subprocess.run([str(GIT),'diff','--cached','--check'],cwd=ROOT,capture_output=True)
    record=dict(exitCode=result.returncode,stdoutBase64=base64.b64encode(result.stdout).decode(),stderrBase64=base64.b64encode(result.stderr).decode(),excludedFiles=[])
    out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record))
    return result.returncode

if __name__=='__main__':raise SystemExit(main())
