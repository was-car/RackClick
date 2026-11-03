"""Reconcile the frozen chosen models with verified development catalogues.

Documentation only: no DB, QA results, application data or ledger is written.
"""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,io,json,unicodedata

ROOT=Path(__file__).resolve().parents[1]
SELECTION=ROOT/'development/hardware/selected-models-506.json'
OUTPUT=ROOT/'docs/COBERTURA-MODELOS-ELEGIDOS'
LINKS=ROOT/'development/hardware/selected-profile-links.json'
LINKS_SHA256='8dd28502a3eca9bcf66bd504a718d266eceaa1503b8bafccc3bf93428428b6ed'
ALIASES={'hpearubanetworking':'aruba','hpearuba':'aruba','aruba':'aruba',
 'junipernetworks':'juniper','juniper':'juniper','glinet':'glinet',
 'startechcom':'startech','startech':'startech'}
def token(s):return ''.join(c for c in unicodedata.normalize('NFKC',s).casefold() if c.isalnum() or c=='+')
def brand(s):return ALIASES.get(token(s),token(s))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def pretty(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8')

def selection(source=None):
 if source:
  raw=read(source);models=[{k:m[k]for k in ('id','manufacturer','model','category','sourcePages')}for m in raw['models']]
  value=dict(schemaVersion=1,scope='Frozen named selection, not all market products or physical revisions',originalEdition=raw['edition'],originalDate=raw['date'],sourceManifestSha256=sha(source),models=models)
  if SELECTION.exists() and SELECTION.read_bytes()!=pretty(value):raise ValueError('selection_changed_requires_separate_version')
 else:value=read(SELECTION)
 assert len(value['models'])==506 and len({m['id']for m in value['models']})==506
 return value

def implemented():
 result=[];wiring=(ROOT/'development/frontend/src/hardware-mounting.ts').read_text(encoding='utf-8')
 for p in sorted((ROOT/'development/hardware').glob('catalog-*-v1.json')):result+=read(p)['definitions']
 for p in sorted((ROOT/'development/hardware').glob('catalog-batch*.manifest.json')) + list((ROOT/'development/hardware').glob('catalog-selected506*.manifest.json')):
  folder=p.name.removeprefix('catalog-').removesuffix('.manifest.json')
  if f'./hardware-{folder}.generated.json'not in wiring:continue
  manifest=read(p)
  for name,pin in {**manifest['inputs'],**manifest['files']}.items():
   target=(ROOT/name).resolve();assert target.is_relative_to(ROOT.resolve()) and sha(target)==pin, name
  for name in manifest['inputs']:
   if not (name.startswith('development/hardware/'+folder+'/')and name.endswith('.json')):continue
   data=read(ROOT/name)
   if name=='development/hardware/selected506k/support.json':
    # This pinned source is a separate synthetic mounting contract, not a SKU.
    # Do not treat arbitrary future JSON as model authoring or silently skip it.
    assert set(data)=={'formatVersion','definitions'} and type(data['formatVersion']) is int and data['formatVersion']==1 and len(data['definitions'])==1,'coverage_support_invalid'
    support=data['definitions'][0]
    assert support['key']=='shelf-7u-deep' and support['revision']=='mount-support7u-20261101-v1' and support['kind']=='shelf' and support['identity']==dict(manufacturer=None,family=None,model=None,sku=None) and support['provenance']['kind']=='own-synthetic','coverage_support_invalid'
    result+=data['definitions']
   else:result += [row['definition']for row in data['models']]
 assert len({(m['key'],m['revision'])for m in result})==len(result)
 # One explicitly reviewed successor adds USP to the same commercial model.
 # Count the existing model once and retain its original coverage binding; this
 # is not a generic latest-revision rule and never changes rendering lookups.
 duplicates={key for key,count in Counter(m['key'] for m in result).items() if count>1}
 if duplicates:
  assert duplicates=={'selected-nb-e5030fe747d79fe6'},'coverage_revision_duplicate_unreviewed'
  revisions={m['revision'] for m in result if m['key']=='selected-nb-e5030fe747d79fe6'}
  assert revisions=={'selected506a-20261101-v1','selected506l-support-20261101-v1'},'coverage_revision_duplicate_unreviewed'
  result=[m for m in result if not(m['key']=='selected-nb-e5030fe747d79fe6' and m['revision']=='selected506l-support-20261101-v1')]
 return [m for m in result if m['identity']['manufacturer']]

def explicit_links(chosen,models):
 assert sha(LINKS)==LINKS_SHA256,'reviewed_profile_links_changed'
 data=read(LINKS)
 assert data['formatVersion']==1 and data['selectionSha256']==sha(SELECTION),'profile_link_selection_mismatch'
 originals={s['id']:s for s in chosen['models']};definitions={(m['key'],m['revision']):m for m in models}
 result={}
 for row in data['links']:
  identifier=row['selectionId'];assert identifier not in result and identifier in originals,'profile_link_duplicate_or_unknown'
  original=originals[identifier]
  assert (row['manufacturer'],row['model'])==(original['manufacturer'],original['model']),'profile_link_model_substitution'
  model=definitions.get((row['profileKey'],row['profileRevision']));assert model is not None,'profile_link_revision_unknown'
  assert token(model['identity']['sku'])==token(row['sourceSku']),'profile_link_sku_mismatch'
  encoded=(json.dumps(model,ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
  assert hashlib.sha256(encoded).hexdigest()==row['definitionSha256'],'profile_link_definition_changed'
  assert sha(ROOT/row['existingAuthoring'])==row['existingAuthoringSha256'],'profile_link_authoring_changed'
  result[identifier]=model
 assert len(result)==7,'reviewed_seven_profile_links_required'
 return result

def outputs(chosen,models,as_of):
 links=explicit_links(chosen,models)
 rows=[];used=set()
 for s in chosen['models']:
  matches=[m for m in models if brand(s['manufacturer'])==brand(m['identity']['manufacturer']) and token(s['model'])in{token(m['identity']['model']),token(m['identity']['sku'])}]
  assert len(matches)<=1,('ambiguous_model',s['id'])
  m=matches[0]if matches else None
  if s['id']in links:
   linked=links[s['id']]
   assert m is None or (m['key'],m['revision'])==(linked['key'],linked['revision']),'profile_link_conflicting_match'
   m=linked
  rows.append(dict(id=s['id'],manufacturer=s['manufacturer'],model=s['model'],category=s['category'],status='perfil_en_desarrollo'if m else'pendiente_de_perfil_correspondiente',profileKey=m['key']if m else'',profileRevision=m['revision']if m else''))
  if m:used.add(m['key'])
 covered=sum(bool(x['profileKey'])for x in rows);pending=len(rows)-covered;additional=len(models)-len(used)
 assert covered==len(used),'A profile must not count twice in this frozen selection'
 counts=dict(selected=len(rows),commercialProfiles=len(models),selectedWithProfile=covered,selectedPending=pending,additionalCommercialProfiles=additional,minimum500Remaining=max(0,500-len(models)),selectedCoveragePercent=round(100*covered/len(rows),2))
 categories=dict(Counter(x['category']for x in rows if not x['profileKey']))
 report=dict(schemaVersion=1,asOf=as_of,selectionSha256=hashlib.sha256(pretty(chosen)).hexdigest(),counts=counts,matching='Exact normalized model OR SKU within closed manufacturer aliases, plus seven pinned independently reviewed SKU links. NFKC/casefold/alnum preserves plus. No substring or neighbouring-model substitution. This does not prove all hardware revisions or QA acceptance.',profileLinksSha256=LINKS_SHA256,manufacturerAliases=ALIASES,pendingByCategory=categories,rows=rows,additionalModels=[dict(key=m['key'],revision=m['revision'],**m['identity'])for m in models if m['key']not in used],writesLedger=False,globalProductPercentageCalculated=False)
 labels={'ap':'Puntos de acceso','firewall':'Firewalls','nas':'NAS','other':'Otros equipos','patch-panel':'Patch panels','pdu':'PDU','rack':'Racks','router':'Routers','server':'Servidores','shelf':'Bandejas','storage':'Almacenamiento','switch':'Switches','ups':'UPS / SAI'}
 table=''.join(f'| {labels.get(k,k)} | {v} |\n'for k,v in sorted(categories.items()))
 percentage=f"{counts['selectedCoveragePercent']:.2f}".replace('.',',')
 groups=Counter(m['revision'].split('-')[0] for m in models if m['key'].startswith('selected-') and m['key'] in used)
 groups_text=', '.join(f'{count} de {revision}' for revision,count in sorted(groups.items()))
 doc=f'''# Cobertura de los modelos elegidos

Fecha de conciliación: {as_of}. [Lista original fija](../development/hardware/selected-models-506.json) · [Estado por modelo JSON](COBERTURA-MODELOS-ELEGIDOS.json) · [CSV de los 506](COBERTURA-MODELOS-ELEGIDOS.csv).

| Alcance | Con perfil en desarrollo | Pendientes |
|---|---:|---:|
| Objetivo de al menos 500 modelos comerciales | {len(models)} | {counts['minimum500Remaining']} para alcanzar 500 |
| Los {len(rows)} modelos concretos de la selección original | {covered} | **{pending}** |

Las tandas ampliaron la cartera con **{additional} modelos adicionales** que no coinciden con la selección original. Por eso llegar a 500 en total y completar los 506 elegidos son resultados distintos. La cobertura de identidades de aquella selección es {percentage}%; esto no es el porcentaje global del proyecto ni de aceptación QA.

La conciliación anterior sólo por nombres registraba 44 coincidencias. Se añaden siete vínculos de SKU revisados explícitamente en [selected-profile-links.json](../development/hardware/selected-profile-links.json), sin crear duplicados, y los perfiles curados por grupos ({groups_text}). No se introduce un alias general HPE→Aruba. Los límites de consola, RPS y revisiones físicas se conservan.

Hay {len(models)} perfiles comerciales en desarrollo. El resto de perfiles sintéticos se excluye del conteo. Las coincidencias conservan `+`, modelo y SKU; se normalizan sólo formato y alias de fabricante cerrados. Un modelo vecino, otra RAM, una referencia de familia o una foto no sustituyen el perfil seleccionado. Las coincidencias de modelo no certifican todas las revisiones físicas.

## Qué queda de la selección original

| Categoría | Sin perfil correspondiente |
|---|---:|
{table}
Los {pending} pendientes están identificados en JSON/CSV. Las siguientes tandas deben salir de esa lista fija; cualquier incorporación fuera de ella se registra por separado. Algunos modelos requieren ampliar antes el contrato de puertos, módulos, alimentación o montaje: no se deben inventar combos independientes, QSFP como SFP, conexiones SAS/FC, capacidad eléctrica o accesorios para completar el dibujo.

El lote 05 histórico aporta cien modelos. Su visor `VER-100-MODELOS-05.html` está disponible en el repositorio completo y en su propio ZIP, fuera de los paquetes de revisión de la selección. Conserva fuentes y vistas sin confirmar explícitas. Revisión visual de Wascar, variantes pendientes y candidata instalada siguen separadas del conteo. La lista original incluye modelos con sólo material de referencia; no declara plantillas instaladas.

Reproducción: `C:/Python312/python.exe -X utf8 -B tools/build_hardware_coverage.py --check --as-of {as_of}`. El auxiliar verifica hashes de los manifiestos de desarrollo y no cambia DB, VM, resultados QA ni pesos del ledger. Índice del cierre restante: 9,76/100, sin nuevo porcentaje global por contar modelos.
'''
 stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 return {SELECTION:pretty(chosen),OUTPUT.with_suffix('.json'):pretty(report),OUTPUT.with_suffix('.md'):doc.encode('utf-8'),OUTPUT.with_suffix('.csv'):('\ufeff'+stream.getvalue()).encode('utf-8')},counts

def main():
 p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--write',action='store_true');mode.add_argument('--check',action='store_true');p.add_argument('--selection-manifest',type=Path);p.add_argument('--as-of',required=True);a=p.parse_args()
 assert token('DS423+')!=token('DS423') and token('EX2300-24T')!=token('EX2300-24P')
 files,counts=outputs(selection(a.selection_manifest),implemented(),a.as_of)
 for path,data in files.items():
  if a.write:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
  else:assert path.is_file() and path.read_bytes()==data,path.name+' stale'
 print(json.dumps(dict(result='written'if a.write else'checked',**counts,writesLedger=False)))
if __name__=='__main__':main()
