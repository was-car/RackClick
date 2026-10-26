"""Coordinator: record immutable guards and the scoped 45-milestone plan."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/cuarenta-y-cinco-tandas-428-472'
E.mkdir(parents=True,exist_ok=True)
if (E/'INICIO.json').exists() or (ROOT/'docs/PLAN-CUARENTA-Y-CINCO-TANDAS-428-472.json').exists():
    raise SystemExit('Initial evidence already exists; refuse to overwrite historical baseline or milestone results.')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((ROOT/'evidence/s1-20261017/treinta-tandas-398-427/INICIO.json').read_text())
guards={p:digest(ROOT/p) for p in old['guards'] if p!='docs/QA-CASOS-WASCAR.json'}
for p in ['evidence/s1-20261017/treinta-tandas-398-427/SHA256SUMS','evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json','docs/QA-CASOS-WASCAR.json']:
    guards[p]=digest(ROOT/p)
start={'utc':datetime.now(timezone.utc).isoformat(),'baseCommit':subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'gitCleanAtFirstRead':True,'initialProgress':76,'actualQa':'185','qaMutationsPlanned':False,'appBuildsPlanned':1,'frontendBuildsPlanned':1,'guards':guards,'mutableCatalogGuardExcludedAtClosure':True}
(E/'INICIO.json').write_text(json.dumps(start,indent=2)+'\n',encoding='utf-8')
groups=[('Contrato y compatibilidad histórica','Contrato de captura versionada sin DDL','DTO y endpoint opt-in con v1 conservado','Eventos antiguos y detalles no disponibles'),('Sedes','Captura transaccional de sedes','Lectura literal antes/después de sedes','Crear/renombrar/borrar sede contra PostgreSQL'),('Edificios','Captura de edificios y padreUUID','Presentación histórica de edificios','CRUD edificios y ámbito real'),('Salas','Captura de salas y padreUUID','Presentación histórica de salas','CRUD salas y aislamiento real'),('Racks','Captura de creación/edición de rack','Presentación de nombre/tamaño/ubicación rack','Creación y edición persistidas'),('Asignación de rack','Captura de sala antes/después','Presentación de la asignación explícita','Asignación y pertenencia persistidas'),('Creación de equipos','Creación normal/catálogo/plantilla persistida','Presentación tipada sin blueprint','Tres caminos de creación contra PostgreSQL'),('Edición de equipos','Captura de atributos editados','Nombres registrados distintos de actor actual','Edición y nombres Unicode históricos'),('Movimiento de equipos','Ubicación previa/posterior por tipo','RackEquipment/Dose/final sin circuitos inventados','Movimiento conservando IDs y permisos'),('Reordenación','Captura del orden persistido','Presentación explícita de sortOrder','Reordenación acotada completa'),('Duplicación','Origen anterior y destino posterior reales','Relación origen/destino explícita','Nuevos IDs y referencia origen histórica'),('Borrado de rack','Captura acotada del rack y afectados','Presentación histórica tras desaparición','Borrado sin consulta de nombres actuales'),('Borrado de equipos','Captura individual y lote porIDs','Presentación de eliminados porID/tipo','Borrado simple/lote con eventos válidos'),('Grupos de puertos','Captura real de configuración y cantidad','GrupoUUID/tipo/prefix explícitos','Edición grupos sin identidad porgn'),('Cierre transversal','Autoridad/redacción/rollback/replay/escala','Edge dos sesiones, borradores y recarga explícita','Revisión independiente, evidencia y guíaQA')]
batches=[]
for index,(group,*titles) in enumerate(groups):
    for offset,title in enumerate(titles):batches.append({'id':428+index*3+offset,'group':group,'title':title,'status':'planned','owner':['backend','frontend','coordinator'][offset],'evidence':None,'independentEvidence':None})
plan={'group':'428-472','count':45,'completed':0,'initialProgress':76,'progressBasis':'docs/PROGRESO-GLOBAL.md','scope':'15 grupos de tres hitos dependientes de captura, presentación y verificación; no45módulos ni45suites. Candidata de desarrollo, QA185 conservado.','batches':batches}
(ROOT/'docs/PLAN-CUARENTA-Y-CINCO-TANDAS-428-472.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'guards':len(guards),'milestones':len(batches),'result':'recorded'}))
