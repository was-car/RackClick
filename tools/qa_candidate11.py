"""Prepare and assess candidate11 QA without installing, adopting or changing the ledger."""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SHA = 'f090b56e13bc3d4670834746cff33a2d01831eae517dbb0343ce760241c567b0'
CANDIDATE = {'edition':'11','schema':43,'archiveSha256':SHA}
SELECTED = ('QA-166','QA-167','QA-165','QA-133','QA-136','QA-139','QA-141',
            'QA-142','QA-162','QA-09','QA-130','QA-163','QA-164','QA-05')
STATUSES = ('Sin probar','Pass','Not Pass','Bloqueado')
EVIDENCE = ('evidence/s1-20261102/punto3','evidence/s1-20261102/demo50','evidence/s1-20261102/windows43')
# Historical point3 parent excluded child indexes with mixed source-snapshot
# scopes. Pin their bytes, without treating source references as current runs.
PARENT_EXCLUDED_INDEXES = {'evidence/s1-20261102/punto3':{
    'json-export/SHA256SUMS.txt':'075850ae13f82c8bc2f7fb117f0cda6715764d8f896dbc6bac5ef5184eec3b91',
    'mfa-backend/SHA256SUMS.txt':'bae7c0a2a614806a9291c1b969e7e61ddfa1eed4459abeb9105f98ee87a4e767',
    'review/SHA256SUMS.txt':'9c8eabfc026f5e4380683a5c5566a5b0ff64ec3044e3f80ca483c0e536a0374b'}}
PENDING = [
    'QA manual del catálogo, los50clientes y permisos de roles en D; las comprobaciones técnicas no rellenan resultados personales.',
    'Resultados manuales de Wascar en esta edición; no trasladar PASS anteriores.',
    'Recuperación con factores MFA: sobre portable/emergencia/rotación no integrados.',
    'Pendientes del punto3: importación/backup desde dashboard y aceptación administrativa.',
    'Redistribución de binarios y adopción final de Wascar.'
]

def digest(data): return hashlib.sha256(data).hexdigest()
def encoded(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def strict_load(text):
    def pairs(rows):
        d={}
        for key,value in rows:
            if key in d: raise ValueError('duplicate_key')
            d[key]=value
        return d
    return json.loads(text,object_pairs_hook=pairs)

def spec(root=ROOT):
    catalog = strict_load((root/'docs/QA-CASOS-WASCAR.json').read_text(encoding='utf-8-sig'))
    lookup = {row['id']:row for row in catalog['cases']}
    cases = [dict(lookup[key],caseSha256=digest(encoded(lookup[key]))) for key in SELECTED]
    return {'format':'RackClickCandidateQaSpecification-v1','candidate':CANDIDATE,
        'scope':'Selected manual cases, not full acceptance or project progress','adoption':False,
        'sourceCatalogRevision':catalog['revision'],'cases':cases,'pending':PENDING}

def exact(value,keys): return type(value) is dict and set(value)==set(keys)
def valid_origin(value):
    if value=='': return True
    if type(value) is not str or len(value)>300 or re.search(r'[\x00-\x20\x7f]',value): return False
    try:
        p=urlsplit(value);port=p.port
        return p.scheme=='https' and bool(p.hostname) and not p.username and not p.password and not p.query and not p.fragment and p.path in ('','/') and (port is None or 1<=port<=65535)
    except ValueError: return False

def assess(data,definition):
    if (not exact(data,('format','candidate','environment','records')) or data['format']!='RackClick-QA-Candidate-v1'
        or not exact(data['candidate'],CANDIDATE) or data['candidate']!=CANDIDATE
        or type(data['candidate']['schema']) is not int): raise ValueError('candidate_mismatch')
    env=data['environment']
    if (not exact(env,('origin','candidateConfirmed')) or type(env['origin']) is not str or not valid_origin(env['origin'])
        or type(env['candidateConfirmed']) is not bool or (env['candidateConfirmed'] and not env['origin'])): raise ValueError('environment_invalid')
    records=data['records'];known={c['id']:c for c in definition['cases']}
    if type(records) is not dict or not set(records)<=set(known):raise ValueError('records_invalid')
    counts={s:0 for s in (*STATUSES,'Desactualizado')}
    for key,item in known.items():
        row=records.get(key)
        if row is None:
            if key in records:raise ValueError('record_invalid')
            counts['Sin probar']+=1;continue
        if (not exact(row,('result','notes','caseSha256','updatedUtc')) or row['result'] not in STATUSES
            or type(row['notes']) is not str or len(row['notes'])>20000 or type(row['caseSha256']) is not str
            or not re.fullmatch('[a-f0-9]{64}',row['caseSha256']) or type(row['updatedUtc']) is not str
            or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?Z',row['updatedUtc'])):raise ValueError('record_invalid')
        try: datetime.fromisoformat(row['updatedUtc'].replace('Z','+00:00'))
        except ValueError:raise ValueError('record_invalid')
        counts[row['result'] if row['caseSha256']==item['caseSha256'] else 'Desactualizado']+=1
    return {'formatValid':True,'counts':counts,'selectedCases':len(known),
        'manualChecklistComplete':env['candidateConfirmed'] and counts['Pass']==len(known),
        'adoption':False,'productionReady':False,'source':'operator_self_report_not_machine_verification','pending':PENDING}

def audit(root=ROOT):
    from package_windows43 import verify
    package=verify(root/'RackClick-Windows-Completo-11.zip',SHA)
    seals=[]
    for directory in EVIDENCE:
        base=root/directory;seen=set()
        for line in (base/'SHA256SUMS.txt').read_text(encoding='ascii').splitlines():
            expected,name=line.split('  ',1)
            if (not re.fullmatch('[a-f0-9]{64}',expected) or name in seen or ':' in name or name.startswith('/')
                or '\\' in name or '..' in Path(name).parts):raise ValueError('evidence_index_invalid')
            seen.add(name);p=base/name
            if not p.is_file() or p.is_symlink() or digest(p.read_bytes())!=expected:raise ValueError('evidence_mismatch')
        excluded=PARENT_EXCLUDED_INDEXES.get(directory,{})
        child_indexes=[]
        for name in excluded:
            index=base/name
            measured=digest(index.read_bytes())
            if measured!=excluded[name]:raise ValueError('evidence_index_mismatch')
            child_indexes.append({'path':name,'sha256':measured,'scope':'Historical index bytes, source references not reexecuted'})
        actual={p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file() and p!=base/'SHA256SUMS.txt'}
        if actual!=seen|set(excluded):raise ValueError('evidence_inventory_mismatch')
        seals.append({'path':directory,'verifiedFiles':len(seen),'parentExcludedIndexesVerified':child_indexes,
                      'evidenceReusedNotRerun':True})
    return {'status':'PASS','scope':'Read-only integrity, not execution of prior tests','candidate':CANDIDATE,
        'package':package,'evidenceSeals':seals,'adoption':False,'productionReady':False,'pending':PENDING}

def render(definition,root=ROOT):
    esc=html.escape;rows=[]
    for case in definition['cases']:
        warning=''
        if case['id'] in ('QA-09','QA-130','QA-163'):
            warning='<p class="warning">Requiere cuentas de laboratorio preparadas para11 y su ámbito. No uses credenciales de otro entorno ni arriesgues el último administrador. Si no están preparadas, marca Bloqueado.</p>'
        steps=''.join('<li>'+esc(step)+'</li>' for step in case['steps'])
        options=''.join('<option>'+s+'</option>' for s in STATUSES)
        rows.append(f'<details data-case="{case["id"]}"><summary><strong>{case["id"]} · {esc(case["title"])}</strong><span data-badge>Sin probar</span></summary><p>Estado del catálogo: {esc(case["feature"])}. Anota sólo lo probado en11.</p>{warning}<ol>{steps}</ol><p class="expected"><strong>Esperado:</strong> {esc(case["expected"])}</p><div class="results"><label>Resultado<select data-result>{options}</select></label><label>Observaciones, sin secretos<textarea data-notes rows="4" maxlength="20000"></textarea></label></div></details>')
    js=(root/'tools/qa_candidate11.mjs').read_text(encoding='utf-8').replace('export const ','const ').replace('export function ','function ')
    payload=json.dumps(definition,ensure_ascii=False).replace('<',r'\u003c')
    return '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RackClick11 · QA y cierre</title><style>
body{font:16px/1.6 system-ui;max-width:1120px;padding:24px;margin:auto;background:#eef3f8;color:#162e47}h1{font-size:30px}a{color:#105aa0}header,details,.environment{background:white;border:1px solid #c7d4e0;border-radius:10px;padding:20px;margin:16px 0}summary{cursor:pointer;display:flex;gap:16px;justify-content:space-between}summary span{white-space:nowrap;color:#245a79}.warning{border-left:4px solid #bb6513;padding-left:12px}.toolbar{background:#162e47;color:white;position:sticky;top:0;padding:12px;z-index:1;border-radius:8px}button,input,select,textarea{font:inherit;padding:9px;border:1px solid #8aa0b5;border-radius:6px}button{cursor:pointer}label{display:block;margin:8px 0}textarea{width:100%;box-sizing:border-box}.results{display:grid;grid-template-columns:180px 1fr;gap:20px}.expected{border-left:4px solid #237b62;padding:12px}.toolbar input{max-width:230px}#notice{margin:7px 0;color:#ffe1a0}code{overflow-wrap:anywhere}li{padding:5px 0}@media(max-width:700px){body{padding:12px}.results{display:block}summary{display:block}}@media print{.toolbar{display:none}body{background:white}details{break-inside:avoid}}
</style><header><h1>RackClick11 · QA y cierre</h1>
<p>Tu hoja breve de14 casos. Abre cada fila para ver dónde hacer clic, el resultado esperado y tus observaciones. Puedes parar y continuar otro día.</p>
<p><strong>Edición11 · esquema43.</strong> SHA256 del ZIP: <code>'''+SHA+'''</code>.</p>
<p><a href="docs/INSTALADOR11-WINDOWS43.md">Manual de instalación</a> · <a href="GUIA-QA-WASCAR.html">Catálogo general de167casos</a> · <a href="docs/QA-CIERRE-CANDIDATA11.md">Estado y pendientes</a></p>
<p class="warning">La VM debe estar preparada para11. Los casos no están aprobados por existir código. No se actualiza tu servidor actual; no importes resultados de10 u otro laboratorio como PASS nuevo. Esta hoja no conecta ni activa funciones.</p>
</header><div class="toolbar"><button id="export">Guardar mis resultados JSON</button><label style="display:inline">Importar mi copia11 <input id="import" type="file" accept=".json,application/json"></label><button onclick="window.print()">Imprimir</button><p id="summary"></p><p id="notice" role="status">Las notas son locales. Exporta una copia antes de cerrar o cambiar de equipo. No escribas contraseñas, QR ni códigos MFA.</p></div>
<section class="environment"><h2>Antes de marcar resultados</h2><label>URL HTTPS de la instalación que probaste <input id="origin" placeholder="https://IP-del-servidor:5443"></label><label><input id="confirmed" type="checkbox"> He comprobado que mis pruebas corresponden a esta candidata11.</label><p>La URL es una nota tuya; esta página no comprueba que el servidor responda. Completar14casos tampoco adopta el producto. Las pruebas técnicas de VM y la recuperación MFA completa siguen separadas.</p></section>'''+''.join(rows)+f'<script id="qa-spec" type="application/json">{payload}</script><script type="module">{js}</script></html>'

def outputs(root=ROOT):
    definition=spec(root)
    rows='\n'.join(f'| {c["id"]} | {c["title"]} | Sin probar |' for c in definition['cases'])
    md=f'''# QA y cierre · candidata11/esquema43

02.11.2026. [Abrir hoja interactiva](../QA-CIERRE-CANDIDATA11.html). Selección de14casos del catálogo existente: no añade resultados ni pesos al ledger.

ZIP: RackClick-Windows-Completo-11.zip, SHA256 {SHA}. New11 en D ya tiene servicio automático, HTTPS, backup programado y reinicio Windows comprobados como postboot_verified. [Estado y pasos de D](VM11-D-PASOS-QA.md). **Punto6 en curso: no hay aceptación final.**

## Qué hacer

1. Para este ensayo usa D, instalada y reiniciada por Wascar. No vuelvas a instalar ni reviertas el snapshot para hacer QA. Wascar conserva el control del encendido, apagado y snapshots.
2. Abre en D https://192.168.206.133:5443 y el acceso RackClick-VERIFICAR-11-6ca767fa.cmd del Escritorio. Acceso privado muestra las credenciales locales. Conserva el MFA de Wascar. Para instalar tú otra VM limpia sigue [el manual11](INSTALADOR11-WINDOWS43.md), apartados00–03; marca explícitamente la casilla de confianza de CA. No copies DLL/SQL a tu servidor10.
3. D ya tiene50clientes cargados y verificados. No relances el cargador allí. [Corrección02 y límites](CARGADOR-DEMO50-02.md). Para otra instalación43 vacía, usa el ZIP corregido con su SHA externo y sus instrucciones.
4. Abre la hojaHTML y completa por orden. Para permisos/recuperación necesitas cuentas preparadas: si faltan, marcaBloqueado. No arriesgues el último administrador.
5. AnotaPass/NotPass/Bloqueado yobservaciones; pulsaGuardar mis resultadosJSON antes de cerrar. Esta hoja rechaza otras candidatas y conserva casos no incluidos en tu importación. Si cambia un guion conserva notas, pero pide repetirlo.
6. Desde el panel oficial conserva Verificar instalación y el informe sanitizado del Escritorio/RECOPILAR-INFORME.cmd. Devuelve eseZIP ytuJSONmanual; no adjuntes acceso privado,dumps,claves ocódigos. No hace falta otro colector.

| Caso | Prueba | Resultado inicial |
|---|---|---|
{rows}

Los casos condicionales mantienen identidad/texto del catálogo. No se crean cuentasTécnicoA/B/Lector ni se activan casos globales por generar esta hoja. URL,confirmación yresultados son declaración del operador, no medición autenticada.

## Qué impide el cierre global

'''+''.join('- '+p+'\n' for p in PENDING)+'''

La edición10 conserva sus resultados. Releerhashes/sellos verifica integridad hoy; no vuelve a ejecutar ensayos. Las68pruebas/40focos/50clientes previos no se cuentan otra vez. Catálogo506/506=100% de selección; índice acreditado9,76/100, sin porcentaje global nuevo.

## Reproducir y valorar una copia

    C:/Python312/python.exe -X utf8 -B tools/qa_candidate11.py --write
    C:/Python312/python.exe -X utf8 -B tools/qa_candidate11.py --check
    C:/Python312/python.exe -X utf8 -B tools/qa_candidate11.py --audit
    C:/Python312/python.exe -X utf8 -B tools/qa_candidate11.py --assess 'RUTA/Resultados-QA-RackClick-11-fecha.json'

No cambia producto,DB,VM,servicios,ledger,ZIP ni respuestas personales. --assess mantiene adoption=false incluso con todos losPass y no habilita producción.
'''
    return {root/'docs/QA-CIERRE-CANDIDATA11.json':json.dumps(definition,ensure_ascii=False,indent=2)+'\n',
            root/'docs/QA-CIERRE-CANDIDATA11.md':md,root/'QA-CIERRE-CANDIDATA11.html':render(definition,root)}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--write',action='store_true');g.add_argument('--check',action='store_true');g.add_argument('--audit',action='store_true');g.add_argument('--assess',type=Path)
    a=p.parse_args(argv)
    try:
        if a.audit:result=audit()
        elif a.assess:
            if a.assess.stat().st_size>2000000:raise ValueError('report_size_invalid')
            result=assess(strict_load(a.assess.read_text(encoding='utf-8-sig')),spec())
        else:
            generated=outputs()
            if a.write:
                for path,text in generated.items():path.write_text(text,encoding='utf-8')
            elif any(not path.is_file() or path.read_text(encoding='utf-8')!=text for path,text in generated.items()):raise ValueError('qa_outputs_stale')
            result={'valid':True,'selectedCases':len(SELECTED),'adoption':False,'writesProductOrLedger':False}
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,OSError,KeyError,TypeError):
        print(json.dumps({'valid':False,'code':'qa_candidate11_rejected','adoption':False}));return 1

if __name__=='__main__':sys.exit(main())
