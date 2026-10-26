"""Open only a synthetic new-candidate XLS in an owned Excel instance, read-only."""
import argparse,hashlib,json,os,platform,subprocess,time
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Cells(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.cell=None;self.values=[]
    def handle_starttag(self,tag,attrs):
        if tag in ['td','th']:
            assert self.cell is None;self.cell=''
    def handle_data(self,data):
        if self.cell is not None:self.cell+=data
    def handle_endtag(self,tag):
        if tag in ['td','th']:
            assert self.cell is not None
            if self.cell:self.values.append(self.cell)
            self.cell=None
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--artifact',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);raw=a.artifact.read_bytes();parser=Cells();parser.feed(raw.decode('utf-8'));assert parser.cell is None
    safety=['=1+1','+1+1','-2+3','@SUM(1,2)','000001','Ω 日本語 🐈']
    assert all(value in parser.values for value in safety),'Office fixture must include literal safety controls'
    expected=a.output/'expected.json';expected.write_bytes((json.dumps(dict(sha256=sha(a.artifact),cells=parser.values,safetyLiterals=safety),ensure_ascii=False,indent=2)+'\n').encode())
    helper=Path(__file__).with_name('Test-Rc9Excel832.ps1');sources={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),helper]}
    cmd=[str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(helper),'-ArtifactPath',str(a.artifact.resolve()),'-ExpectedPath',str(expected.resolve()),'-OutputPath',str((a.output/'office.json').resolve())]
    started=time.monotonic()
    env={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'}
    with (a.output/'execution.log').open('xb') as log:r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
    office=json.loads((a.output/'office.json').read_bytes()) if (a.output/'office.json').exists() else None
    record=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),exitCode=r.returncode,seconds=round(time.monotonic()-started,3),command=cmd,sources=sources,sourcesUnchanged=all(sha(ROOT/p)==h for p,h in sources.items()),artifactSha256=sha(a.artifact),successful=r.returncode==0 and bool(office and office['successful']),actualQaAccessed=False,officialDocumentation=['https://learn.microsoft.com/en-us/office/vba/api/excel.workbooks.open','https://learn.microsoft.com/en-us/office/vba/api/excel.range.hasformula'],limits='One installed Excel version and synthetic file only; not LibreOffice/all Office versions or a guarantee of three actual worksheets. No Office policy changes or user workbooks.')
    (a.output/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record));return 0 if record['successful'] else 1
if __name__=='__main__':raise SystemExit(main())
