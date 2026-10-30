"""Append the independent UTF-8 correction without rewriting earlier execution records."""
import hashlib
import json
from pathlib import Path
from verify_integration1149 import sha

ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-1090-1149';E=ROOT/ER
NOTE='''**Adenda1090–1149 · P2 de codificación corregido.** La revisión independiente encontró constantes deformadas en el auxiliar de pruebas de guía: read_text sin encoding usó cp1252 en Windows al reescribir UTF-8. El catálogo, los HTML y los resultados de Wascar estaban intactos. Se archivaron el auxiliar corrupto y el helper, se restauraron los bytes fuera de la clase autorizada y se fijó UTF-8 explícito. Foco nuevo3/3 PASS: igualdad AST exterior, prefijo/sufijo por bytes y disponibilidad. El47/47 anterior se conserva con su límite; verificación/diff02 posteriores. Sin repetir PostgreSQL ni compilar; global78 % sin aumento. PRUEBA'''

def main():
    output=E/'CORRECCION-GUIA-UTF8.json';assert not output.exists()
    focus=json.loads((E/'QA-FOCO-02.json').read_bytes());assert focus['successful'] and focus['testsRun']==3
    records={}
    for name,link in [('docs/CONTINUIDAD-CODEX.md','../'+ER+'/QA-FOCO-02.json'),('CHANGELOG.md',ER+'/QA-FOCO-02.json'),(ER+'/CIERRE.md','QA-FOCO-02.json')]:
        path=ROOT/name;before=path.read_bytes();heading,sep,rest=before.partition(b'\n');nl=b'\r\n' if heading.endswith(b'\r') else b'\n'
        assert b'Adenda1090' not in before
        note=NOTE.replace('PRUEBA','[Prueba focal]('+link+').').encode().replace(b'\n',nl)
        path.write_bytes(heading+sep+nl+note+nl+nl+rest)
        records[name]=dict(beforeSha256=hashlib.sha256(before).hexdigest(),afterSha256=sha(path))
    plan=ROOT/'docs/PLAN-SESENTA-TANDAS-1090-1149.json';data=json.loads(plan.read_bytes())
    next(b for b in data['batches'] if b['id']==1143)['correctionEvidence']=ER+'/QA-FOCO-02.json'
    plan.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    output.write_text(json.dumps(dict(successful=True,finding='P2-UTF8-GUIA',files=records,
        priorExecutionRecordsPreserved=True,postgresTestsRepeated=0,productBuilds=0,progress=78),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(successful=True,notes=len(records),progress=78)))

if __name__=='__main__':main()
