"""Enable onboarding cases only after a committed, validated real artifact update."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269'
def main():
 out=E/'QA-MATRIX-1269.json';assert not out.exists()
 actual=json.loads((E/'REAL-QA-UPDATE-01.json').read_bytes());validated=json.loads((E/'REAL-QA-VALIDATE-01.json').read_bytes())
 assert actual['valid'] and actual['state']=='committed' and validated['valid'] and validated['selectedRevision']==1209
 target=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json').read_bytes());source=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json').read_bytes())
 pair=lambda m:dict(bundle=m['distributions']['frontend']['app.js'],dll=m['distributions']['server']['RackClick.Server.dll'])
 new,old=pair(target),pair(source);directory=Path(json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes())['directory']);assert directory.resolve()==(ROOT/actual['directory']).resolve()
 cfg=json.loads((directory/'manual-qa.json').read_bytes());assert cfg['bundleSha256']==new['bundle'] and cfg['dllSha256']==new['dll']
 path=ROOT/'docs/QA-CASOS-WASCAR.json';before=path.read_bytes();catalog=json.loads(before);original=json.loads(before);assert len(catalog['cases'])==87 and 'adminUserOnboardingBuilds' not in catalog
 saved=E/'qa-guide/source-before';saved.mkdir(parents=True,exist_ok=False);(saved/path.name).write_bytes(before)
 for p in ['tools/windows/qa_guide.py','tools/tests/qa_port_colors969.py','tools/tests/qa_category_colors1089.py','tools/tests/test_qa_relations_status848.py']:(saved/Path(p).name).write_bytes((ROOT/p).read_bytes())
 inherited=[]
 for key,values in catalog.items():
  if key.endswith('Builds') and isinstance(values,list) and old in values and new not in values:
   assert all(isinstance(v,dict) and set(v)=={'bundle','dll'} for v in values);values.append(new);inherited.append(key)
 catalog['adminUserOnboardingBuilds']=[new]
 intros=[
  'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Interfaz1209/esquema13 seleccionada sobre el mismo laboratorio, con datos y resultados conservados. Ejecuta INICIAR-QA-RESTAURADO.cmd; usa su guía y credenciales privadas. Elige Español y pulsa Ctrl+F5.',
  'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Continúa desde QA-85 con el UUID confirmado. Usa un grupo limitado de laboratorio y otro perfil de navegador para comprobar acceso. La navegación no asigna permisos.',
  'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Usa el laboratorio restaurado1209/13. F12/Red/Offline es opcional: si no encuentras el control, anota Bloqueado para esa parte. No revoques al último administrador ni afectes otras sesiones.'
 ]
 for case,intro in zip(catalog['cases'][84:],intros):
  assert case['id'] in ['QA-85','QA-86','QA-87'] and case['feature']=='planned';case['feature']='adminUserOnboardingGui';case['steps'][0]=intro
 assert catalog['cases'][:84]==original['cases'][:84]
 assert all(c['steps'][1:]==o['steps'][1:] and c['expected']==o['expected'] for c,o in zip(catalog['cases'][84:],original['cases'][84:]))
 catalog['revision']='2026-10-18-bloque1210-1269';nl='\r\n' if b'\r\n' in before else '\n';path.write_bytes((json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').replace('\n',nl).encode('utf-8'))
 generator=ROOT/'tools/windows/qa_guide.py';raw=generator.read_bytes();anchor=b"        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),";assert raw.count(anchor)==1 and b"'adminUserOnboardingGui':" not in raw
 generator.write_bytes(raw.replace(anchor,anchor+(b'\r\n' if b'\r\n' in raw else b'\n')+b"        'adminUserOnboardingGui': catalog.get('adminUserOnboardingBuilds', []),"))
 record=dict(sourcePair=old,pair=new,inheritedBuildLists=inherited,caseCount=87,unchangedCompleteCases=84,changedCases=['QA-85','QA-86','QA-87'],changedFields=['feature','steps[0]'],otherStepsAndExpectedUnchanged=True,beforeCatalogSha256=hashlib.sha256(before).hexdigest(),afterCatalogSha256=hashlib.sha256(path.read_bytes()).hexdigest(),manualWascarResultsWritten=False,qaDatabaseDml=False)
 with out.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
 print(json.dumps(dict(cases=87,inheritedLists=len(inherited),newlyAvailable=record['changedCases'],manualResultsWritten=False)))
if __name__=='__main__':main()
