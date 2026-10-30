"""Enable category-palette QA only after real schema13 selection and validation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149'
def main():
 out=E/'QA-MATRIX-1149.json';assert not out.exists()
 activated=json.loads((E/'REAL-QA-ACTIVATE-01.json').read_bytes());validated=json.loads((E/'REAL-QA-VALIDATE-01.json').read_bytes())
 assert activated['valid'] and activated['state']=='committed' and activated['selectedRevision']==1089
 assert validated['valid'] and validated['selectedRevision']==1089
 target=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json').read_bytes())
 source=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029/CANDIDATA969-FIX02.json').read_bytes())
 pair=lambda m:dict(bundle=m['distributions']['frontend']['app.js'],dll=m['distributions']['server']['RackClick.Server.dll'])
 new,old=pair(target),pair(source);directory=Path(json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes())['directory'])
 assert directory.resolve()==(ROOT/activated['candidateDirectory']).resolve();cfg=json.loads((directory/'manual-qa.json').read_bytes())
 assert cfg['bundleSha256']==new['bundle'] and cfg['dllSha256']==new['dll']
 path=ROOT/'docs/QA-CASOS-WASCAR.json';before=path.read_bytes();catalog=json.loads(before);original=json.loads(before)
 assert len(catalog['cases'])==84 and 'userCategoryColorsBuilds' not in catalog
 inherited=[]
 for key,values in catalog.items():
  if key.endswith('Builds') and isinstance(values,list) and old in values and new not in values:
   assert all(isinstance(v,dict) and set(v)=={'bundle','dll'} for v in values);values.append(new);inherited.append(key)
 catalog['userCategoryColorsBuilds']=[new]
 intros=[
  'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. La candidata1089/esquema13 está seleccionada en una copia nueva. Ejecuta INICIAR-QA-RESTAURADO.cmd y usa su guía y credenciales privadas. Elige Español y pulsa Ctrl+F5; tus resultados anteriores se conservan.',
  'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Usa la nueva copia QA1089/esquema13 y la cuenta Técnico de su CMD. El origen969 y su recuperación849 se conservan; crea conexiones sólo en el laboratorio autorizado.',
  'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Usa QA1089/esquema13 con perfiles de navegador separados. La parte F12/Red/Offline es opcional: si no localizas el control, registra Bloqueado para esa parte, sin afectar a otras personas.'
 ]
 for case,intro in zip(catalog['cases'][81:],intros):
  assert case['id'] in ['QA-82','QA-83','QA-84'] and case['feature']=='planned';case['feature']='userCategoryColorsGui';case['steps'][0]=intro
 assert catalog['cases'][:81]==original['cases'][:81]
 assert all(c['steps'][1:]==o['steps'][1:] and c['expected']==o['expected'] for c,o in zip(catalog['cases'][81:],original['cases'][81:]))
 catalog['revision']='2026-10-18-bloque1090-1149';nl='\r\n' if b'\r\n' in before else '\n'
 path.write_bytes((json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').replace('\n',nl).encode())
 generator=ROOT/'tools/windows/qa_guide.py';source_bytes=generator.read_bytes()
 anchor=b"        'userPortColorsGui': catalog.get('userPortColorsBuilds', []),";assert source_bytes.count(anchor)==1 and b"'userCategoryColorsGui':" not in source_bytes
 added=(b'\r\n' if b'\r\n' in source_bytes else b'\n')+b"        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),"
 saved=E/'qa-guide/source-before';saved.mkdir(parents=True,exist_ok=False);(saved/'qa_guide.py').write_bytes(source_bytes)
 for name in ['qa_port_colors969.py','qa_category_colors1089.py','test_qa_relations_status848.py']:(saved/name).write_bytes((ROOT/'tools/tests'/name).read_bytes())
 generator.write_bytes(source_bytes.replace(anchor,anchor+added))
 record=dict(sourcePair=old,pair=new,inheritedBuildLists=inherited,caseCount=84,unchangedCompleteCases=81,changedCases=['QA-82','QA-83','QA-84'],changedFields=['feature','steps[0]'],
  otherStepsAndExpectedUnchanged=True,beforeCatalogSha256=hashlib.sha256(before).hexdigest(),afterCatalogSha256=hashlib.sha256(path.read_bytes()).hexdigest(),manualWascarResultsWritten=False,qaDatabaseDml=False)
 with out.open('x',encoding='utf-8') as f:f.write(json.dumps(record,indent=2)+'\n')
 print(json.dumps(dict(cases=84,inheritedLists=len(inherited),newlyAvailable=['QA-82','QA-83','QA-84'],manualResultsWritten=False)))
if __name__=='__main__':main()
