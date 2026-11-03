"""Package reviewed inventory-only Demo50 files; never include a DB or access file."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
from build_demo50_plan import build_plan, load_definitions, plan_bytes, validate_plan

COLLECTIONS={'sites','buildings','rooms','racks','devices','portGroups','ports','connections'}
def sha(data):return hashlib.sha256(data).hexdigest()
def unique_object(pairs):
 result={}
 for key,value in pairs:
  if key in result:raise ValueError('duplicate_json_key')
  result[key]=value
 return result
def parse(data):return json.loads(data.decode('utf-8'),object_pairs_hook=unique_object)

def collect(directory):
 directory=Path(directory).absolute()
 if directory.is_symlink() or directory.is_junction():raise ValueError('portable_root_reparse')
 manifest=parse((directory/'manifest.json').read_bytes());customers=manifest['customers']
 if set(manifest)!={'format','schemaVersion','inventoryOnly','securityIncluded','productionDefault','customers'} or manifest.get('inventoryOnly') is not True or manifest.get('format')!='RackClickDemo50Inventory-v1' or manifest.get('schemaVersion')!=43 or manifest.get('securityIncluded') is not False or manifest.get('productionDefault') is not False:raise ValueError('manifest_scope_invalid')
 if len(customers)!=50 or {c['key'] for c in customers}!={f'c{i:02}' for i in range(1,51)} or len({c['customerId'] for c in customers})!=50:raise ValueError('fifty_distinct_customers_required')
 files={};summary=[];projects={}
 allowed={'manifest.json','plan.json','coverage-matrix.json'}|{c['file'] for c in customers}
 if {p.name for p in directory.iterdir()}!=allowed:raise ValueError('unexpected_portable_file')
 for c in customers:
  if set(c)!={'key','name','scenario','language','customerId','file','sha256','bytes','revision'}:raise ValueError('customer_manifest_scope_invalid')
  if not re.fullmatch(r'c[0-9]{2}\.inventory\.json',c['file']) or c['file']!=c['key']+'.inventory.json':raise ValueError('inventory_filename_invalid')
  p=directory/c['file']
  if not p.is_file() or p.is_symlink() or p.is_junction():raise ValueError('inventory_reparse_or_missing')
  data=p.read_bytes()
  if sha(data)!=c['sha256'] or len(data)!=c['bytes'] or len(data)>4194304:raise ValueError('inventory_digest_invalid')
  value=parse(data)
  if set(value)!={'formatVersion','kind','scope','customerId','revision','inventory'} or value['formatVersion']!=1 or value['kind']!='RackClickInventory' or value['scope']!='customer' or value['customerId']!=c['customerId'] or value['revision']!=c['revision'] or set(value['inventory'])!=COLLECTIONS:raise ValueError('inventory_scope_invalid')
  projects[c['customerId']]=value['inventory'];files[c['file']]=data
  summary.append(c|{'counts':{k:len(value['inventory'][k]) for k in sorted(COLLECTIONS)}})
 for name in ('manifest.json','plan.json','coverage-matrix.json'):
  p=directory/name
  if p.is_symlink() or p.is_junction() or not p.is_file():raise ValueError('metadata_reparse_or_missing')
  files[name]=p.read_bytes();parse(files[name])
 matrix=parse(files['coverage-matrix.json'])
 plan=parse(files['plan.json']);definitions=load_definitions();validate_plan(plan,definitions)
 if plan_bytes(plan)!=plan_bytes(build_plan(definitions,plan['seed'])):raise ValueError('noncanonical_generated_plan')
 if set((x['profileKey'],x['profileVersion']) for x in matrix)!={(x['profileKey'],x['profileVersion']) for x in plan['catalog']}:raise ValueError('catalogue_pair_mismatch')
 if len(matrix)!=868 or len({(x['profileKey'],x['profileVersion']) for x in matrix})!=868:raise ValueError('catalogue_coverage_invalid')
 for x in matrix:
  if set(x)!={'profileKey','profileVersion','customerKey','customerId','resourceId','deviceId','rackId','roomId','supportId','groupIds','portIds','groupCount','portCount','powerEnds','powerEndsConnected','connectionIds','connectionApplicability','reason'}:raise ValueError('coverage_metadata_scope_invalid')
  inventory=projects[x['customerId']];resources={v['id']:v for v in inventory['devices']+inventory['racks']}
  resource=resources.get(x['resourceId'])
  if not resource or resource.get('hardwareProfileKey')!=x['profileKey'] or resource['properties']['hardwareProfileVersion']!=x['profileVersion']:raise ValueError('coverage_resource_not_in_inventory')
  own_ports=[p for p in inventory['ports'] if p['deviceId']==x['deviceId']];own_groups=[g for g in inventory['portGroups'] if g['deviceId']==x['deviceId']]
  if set(x['portIds'])!={p['id'] for p in own_ports} or set(x['groupIds'])!={g['id'] for g in own_groups} or x['groupCount']!=len(own_groups) or x['portCount']!=len(own_ports):raise ValueError('coverage_endpoint_mismatch')
  cables=[c for c in inventory['connections'] if c['fromPortId'] in set(x['portIds']) or c['toPortId'] in set(x['portIds'])]
  power=[p for p in own_ports if p['type'] in {'power','power_dc'}];used={v for c in cables for v in (c['fromPortId'],c['toPortId'])}
  if set(x['connectionIds'])!={c['id'] for c in cables} or x['powerEnds']!=len(power) or x['powerEndsConnected']!=sum(p['id'] in used for p in power):raise ValueError('coverage_connection_mismatch')
  expected_reason=None if own_groups else 'No materialized own connectors in approved profile; mount/capacity checked without invented ports.'
  if x['connectionApplicability']!=('tested' if own_groups else 'not_applicable') or x['reason']!=expected_reason:raise ValueError('coverage_reason_invalid')
 return files,summary,matrix

def viewer(summary):
 data=json.dumps(summary,ensure_ascii=False).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
 return ('''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RackClick · 50 clientes sintéticos</title>
<style>body{margin:0;background:#101820;color:#e9f2f7;font:16px system-ui}main{max-width:1150px;margin:auto;padding:28px}h1{color:#35d7bd}p{line-height:1.6}input{width:95%;padding:12px;background:#1b2833;color:inherit;border:1px solid #678;border-radius:5px}table{border-collapse:collapse;width:100%;margin-top:20px}td,th{text-align:left;padding:12px;border-bottom:1px solid #345}a{color:#6ee7cb}small{color:#b7c9d5}.scroll{overflow:auto}#detail{background:#192630;padding:16px;white-space:pre-wrap}button{background:#263d49;color:white;padding:7px;border:1px solid #789;border-radius:4px}</style>
<main><h1>RackClick · 50 clientes sintéticos</h1><p>Inventario de revisión con 868 perfiles/revisiones. Los nombres y ubicaciones son ficticios. Cada cliente tiene área de negocio y muestras de catálogo, identificadas por separado.</p><p><b>Este visor no se conecta a RackClick ni importa datos.</b> La prueba funcional del servidor y la instalación Windows son comprobaciones distintas. Los JSON excluyen cuentas, sesiones, contraseñas y MFA. Las notas y metadatos de inventario sí forman parte del archivo.</p>
<label for="query">Buscar cliente, escenario o idioma</label><input id="query" placeholder="Por ejemplo: colegio, industria, Büro…"><p id="total"></p><div class="scroll"><table><thead><tr><th>Cliente ficticio</th><th>Escenario</th><th>Racks</th><th>Equipos</th><th>Cables</th><th>Archivo</th></tr></thead><tbody id="rows"></tbody></table></div><p><small>Detalles del cliente seleccionado; no es un plano de ingeniería ni simula el hardware.</small></p><div id="detail">Selecciona Detalles en una fila.</div><script id="data" type="application/json">'''+data+'''</script>
<script>const data=JSON.parse(document.getElementById('data').textContent),rows=document.getElementById('rows');function render(){const q=document.getElementById('query').value.toLocaleLowerCase(),visible=data.filter(c=>[c.key,c.name,c.scenario,c.language].join(' ').toLocaleLowerCase().includes(q));rows.replaceChildren();for(const c of visible){const tr=document.createElement('tr');tr.dataset.customerKey=c.key;for(const v of [c.name,c.scenario,c.counts.racks,c.counts.devices,c.counts.connections]){const td=document.createElement('td');td.textContent=String(v);tr.append(td)}const td=document.createElement('td'),a=document.createElement('a'),b=document.createElement('button');a.href=c.file;a.download=c.file;a.textContent='JSON';b.textContent='Detalles';b.onclick=()=>{document.getElementById('detail').textContent=c.name+'\\nIdioma de referencia: '+c.language+'\\nRevisión: '+c.revision+'\\nSHA256: '+c.sha256+'\\n'+JSON.stringify(c.counts,null,2)};td.append(a,document.createTextNode(' '),b);tr.append(td);rows.append(tr)}document.getElementById('total').textContent=visible.length+' de 50 clientes'}document.getElementById('query').addEventListener('input',render);render();</script></main></html>''').encode('utf-8')

def build(directory,output):
 output=Path(output)
 if output.exists() or output.with_suffix(output.suffix+'.sha256').exists():raise ValueError('output_exists')
 files,summary,matrix=collect(directory)
 files['VER-50-CLIENTES.html']=viewer(summary)
 files['00-LEEME.md']=('''# RackClick · Demo50 · inventario opcional

50 clientes ficticios, siete escenarios, todas las 868 parejas perfil/revisión de esquema43 y conexiones persistidas y probadas. Las áreas de negocio se separan de las muestras de catálogo. La matriz muestra instancias, UUID, grupos, puertos y conexiones; 24 perfiles sin extremos propios quedan no aplicables con motivo, sin puertos inventados.

Extrae el ZIP en una carpeta nueva y abre VER-50-CLIENTES.html con el navegador. Busca un cliente y usa Detalles o descarga su JSON. SHA256SUMS.txt fija cada archivo. No hay ejecutables, fotos de proveedor, bases, cuentas, sesiones, contraseñas, factores MFA ni cadena PostgreSQL.

No es un instalador, un backup PostgreSQL ni el Full Backup original RC9. Los JSON son RackClickInventory-v1 por cliente: la importación desde el panel sigue pendiente. No copies archivos a una base instalada. La selección opcional de esta demo en el paquete completo corresponde al punto5 y no está habilitada en el instalador actual.

Para reproducir el laboratorio nuevo desde el repositorio: docs/LABORATORIO-50-CLIENTES.md, tools/build_demo50_plan.py y tools/prepare_demo50.py. Las herramientas están fijadas por el proyecto. Los UUID de recursos proceden del servidor; semilla e identidades lógicas/requestId son reproducibles. Cada ejecución nueva genera credenciales y recursos nuevos; repetir sobre una salida existente se rechaza.

Los verificadores de puertos genéricos son fixtures sintéticos rotulados, no otros productos de fabricante. Los enlaces entre edificios representan un campus de laboratorio; no inventan circuitos WAN ni certifican transceptores, longitud o parámetros eléctricos. El backup PostgreSQL de recuperación y las credenciales se conservan exclusivamente en .local y no están en este ZIP.
''').encode('utf-8')
 stream=io.StringIO(newline='');writer=csv.writer(stream);writer.writerow(['profileKey','profileVersion','customerKey','resourceId','groupCount','portCount','powerEnds','powerEndsConnected','connectionApplicability'])
 for m in matrix:writer.writerow([m[k] for k in ['profileKey','profileVersion','customerKey','resourceId','groupCount','portCount','powerEnds','powerEndsConnected','connectionApplicability']])
 files['COBERTURA-868.csv']=stream.getvalue().encode('utf-8')
 files['SHA256SUMS.txt']=''.join(sha(data)+'  '+name+'\n' for name,data in sorted(files.items())).encode('ascii')
 def archive():
  buffer=io.BytesIO()
  with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for name,data in sorted(files.items()):
    info=zipfile.ZipInfo('RackClick-Demo50-01/'+name,date_time=(2026,11,2,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
  return buffer.getvalue()
 payload=archive()
 if payload!=archive():raise ValueError('archive_not_reproducible')
 with output.open('xb') as f:f.write(payload)
 with zipfile.ZipFile(output) as z:
  assert z.testzip() is None and len(z.infolist())==len(files)
  assert all(z.read('RackClick-Demo50-01/'+name)==value for name,value in files.items())
 sidecar=output.with_suffix(output.suffix+'.sha256')
 with sidecar.open('x',encoding='ascii') as f:f.write(sha(payload)+'  '+output.name+'\n')
 return {'result':'PASS','files':len(files),'customers':len(summary),'profileRevisions':len(matrix),'bytes':len(payload),'sha256':sha(payload),'noSecurityOrExecutableFiles':True,'twoBuildsByteIdentical':True}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--portable',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();print(json.dumps(build(a.portable,a.output)))
