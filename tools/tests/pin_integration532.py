"""Add only the exact frozen532 application to the closed local integration profiles."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-473-532'
def main():
    p=E/'CANDIDATA532.json';m=json.loads(p.read_text());h=hashlib.sha256(p.read_bytes()).hexdigest();size=m['totalBytes']
    assert m['schema']==9 and m['fileCount']==36 and all(len(m['distributions'][s])==18 for s in ['server','frontend'])
    source=ROOT/'tools/windows/qa_artifact9_source532.py';s=source.read_text(encoding='utf-8');old='TARGET532 = None  # Closed until the coordinator freezes and independently reviews the exact manifest.'
    assert old in s;s=s.replace(old,"TARGET532 = ('evidence/s1-20261018/sesenta-tandas-473-532/CANDIDATA532.json', '"+h+"')");ast.parse(s);source.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
    builder=ROOT/'tools/package_offline_bundle.py';s=builder.read_text(encoding='utf-8');anchor='# These are reviewed application manifests, not caller-provided version/hash overrides.'
    assert 'APPLICATION_CONFIG_SHA256' not in s;s=s.replace(anchor,'APPLICATION_CONFIG_SHA256 = "'+h+'"\n'+anchor)
    old='APPLICATION_XLSX_SHA256: {"name": "397", "files": {"server": 18, "frontend": 18}, "bytes": 6653702}}'
    assert old in s;s=s.replace(old,old[:-1]+',\n    APPLICATION_CONFIG_SHA256: {"name": "532", "files": {"server": 18, "frontend": 18}, "bytes": '+str(size)+'}}');ast.parse(s);builder.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
    reader=ROOT/'tools/windows/RackClick.OfflineBundle.ps1';s=reader.read_text(encoding='utf-8');old="        default {Stop-OfflineBundleCheck 'application_pin_mismatch'}"
    assert s.count(old)==1;s=s.replace(old,"        '"+h+"' {return @{name='532';server=18;frontend=18;bytes="+str(size)+"L}}\n"+old);reader.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
    print(json.dumps({'closedManifest532':h,'applicationBytes':size,'oldProfilesRetained':['337','397'],'legacyQaOperatorsUntouched':True}))
if __name__=='__main__':main()
