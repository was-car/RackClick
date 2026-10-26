"""Narrow the pre-operation guard to static inputs; PG data is verified logically."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269'
initial=json.loads((E/'INICIO.json').read_bytes());prefix=initial['sourceDirectory']+'/'
removed=[p for p in initial['guards'] if p.startswith(prefix) and '/' in p[len(prefix):] and p[len(prefix):].split('/')[0] not in ['server','frontend','versions']]
for p in removed:del initial['guards'][p]
initial['guardClarification']='INICIO.json original retained. Initial helper accidentally included PG physical files under data/rc_*; removed here before any operation. These necessarily change on startup. Current logical tables/history/OIDs/grants/activity of both DBs are separately guarded by the updater; no database operation has occurred.'
with (E/'INICIO-02.json').open('x',encoding='utf-8') as f:json.dump(initial,f,ensure_ascii=False,indent=2);f.write('\n')
with (E/'GUARDAS-ALCANCE-02.json').open('x',encoding='utf-8') as f:json.dump(dict(excludedPhysicalPgFiles=len(removed),staticFiles=len(initial['guards']),preOperation=True,originalPreserved='INICIO.json',scope=initial['guardClarification']),f,ensure_ascii=False,indent=2);f.write('\n')
print(len(initial['guards']))
