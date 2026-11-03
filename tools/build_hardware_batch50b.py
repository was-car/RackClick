"""Compile the second 50-model batch; schema24 and previous sources stay pinned."""
from __future__ import annotations
import argparse,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).absolute().parents[1]
spec=importlib.util.spec_from_file_location('batch50b_isolated_shared_engine',ROOT/'tools/build_hardware_batch50.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
c=b.c;g=b.g
REVISION='batch50b-20261031-v1'
b.REVISION=REVISION # This is a private module instance, never the historical compiler process.
SOURCES=['development/hardware/batch50b/'+s+'.json' for s in ('synology','qnap','network')]
COUNTS=[15,15,20]
LOCK='development/hardware/catalog-schema25.lock.json'
BASE='development/server/database/024-batch50-hardware.sql'
SERVER='development/server/src/RackClick.Server/Batch50BHardwareProfiles.Generated.cs'
FRONTEND='development/frontend/src/hardware-batch50b.generated.json'
SQL='development/server/database/025-batch50b-hardware.sql'
MANIFEST='development/hardware/catalog-batch50b.manifest.json'
TARGETS='development/server/src/RackClick.Server/Batch50BHardware.Generated.targets'
TOOL='tools/build_hardware_batch50b.py'
SHARED='tools/build_hardware_batch50.py'
EXPECTED_LOCK_SHA256='00c9508e74d996578ef5e08e779c280c2a6c4b54c96435d4c84fbf23c2c625cb'
STATE='curated_development_not_a_release'

def previous_models(root):
    models=[]
    for p in sorted(c.path(root,'development/hardware').glob('catalog-*-v1.json')):
        models+=c.load(p.read_bytes())['definitions']
    for p in sorted(c.path(root,'development/hardware/batch50').glob('*.json')):
        models += [r['definition'] for r in c.load(p.read_bytes())['models']]
    c.require(len(models)==61,'batch50b_baseline_invalid')
    return models

def compile_catalog(root):
    names=[*SOURCES,LOCK,BASE,SHARED,TOOL]
    # Prior authoring is part of the pin set, so duplicate rejection is reproducible.
    prior_names=sorted([p.relative_to(root).as_posix() for p in c.path(root,'development/hardware').glob('catalog-*-v1.json')]+[p.relative_to(root).as_posix() for p in c.path(root,'development/hardware/batch50').glob('*.json')])
    raw={n:c.path(root,n).read_bytes() for n in [*names,*prior_names]};lock=c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK])==EXPECTED_LOCK_SHA256,'batch50b_lock_not_reviewed')
    c.require(lock['targetSchema']==25 and lock['state']==STATE and lock['sourceSha256']=={n:c.sha(raw[n]) for n in SOURCES} and lock['baseMigrationSha256']==c.sha(raw[BASE]) and lock['sharedCompilerSha256']==c.sha(raw[SHARED]),'batch50b_input_changed')
    rows=[]
    for source,count in zip(SOURCES,COUNTS):
        data=c.load(raw[source]);b.fields(data,'formatVersion revision models')
        c.require(type(data['formatVersion']) is int and data['formatVersion']==1 and data['revision']==REVISION and isinstance(data['models'],list) and len(data['models'])==count,'batch50b_count_invalid')
        rows += [b.validate_model(r) for r in data['models']]
    keys=[r['definition']['key'] for r in rows]
    identities=[tuple(r['definition']['identity'][k] for k in ('manufacturer','model')) for r in rows]
    c.require(len(rows)==50 and len(set(keys))==50 and len(set(identities))==50 and sorted(keys)==lock['modelKeys'],'batch50b_models_invalid')
    old=previous_models(root);old_keys={m['key'] for m in old};old_ids={(m['identity']['manufacturer'],m['identity']['model']) for m in old if m['identity']['manufacturer']}
    c.require(not set(keys)&old_keys and not set(identities)&old_ids,'batch50b_previous_model_duplicate')
    # The reviewed existing shelves are reused; no hidden accessory is counted.
    for row in rows:
        m=row['definition']
        if m['kind']=='desktop':c.require(any(s['kind']=='shelf' and any(all(m['dimensionsMm'][k]<=slot['dimensionsMm'][k] for k in ('width','height','depth')) for slot in s['slots']) for s in old),'batch50b_support_unavailable')
    rows.sort(key=lambda r:r['definition']['key']);models=[r['definition'] for r in rows]
    pins=[dict(key=m['key'],revision=m['revision'],sha256=c.sha(c.canonical(m))) for m in models]
    c.require(pins==lock['definitions'],'batch50b_definition_changed')
    views=[]
    for row in rows:
        m=row['definition'];v=c.projection(dict(definitions=[m]));v['synthetic']=False;p=v['profiles'][0]
        p.update(identity=m['identity'],source=m['provenance']['source'],visual=row['visual'])
        import re
        e=row['evidence'];unverified=any(re.search('unverified',a['match'],re.I) for a in e['referenceAssets'])
        family=any(re.search('family|shared',a['match'],re.I) for a in e['referenceAssets']) or any(re.search('family',x,re.I) for x in e['limits'])
        p.update(referenceScope='unverified_reference' if unverified else 'family_reference' if family else 'model_reference',reviewLimits=e['limits'])
        for group,original in zip(p['groups'],m['groups']):group['powerRole']=original['powerRole']
        views.append(v)
    catalogues=[]
    for view in views:
        prior=next((p for p in catalogues if p['version']==view['version']),None)
        if prior:prior['profiles']+=view['profiles']
        else:catalogues.append(view)
    server=b.server_source(models).replace(b'Batch50HardwareProfiles',b'Batch50BHardwareProfiles').replace(b'build_hardware_batch50.py',b'build_hardware_batch50b.py')
    sql=b'-- Auto-generated second batch50; SQL001-024 unchanged. Nominal dimensions only.\n'+b'\n'.join(line for line in g.sql_source(models,pins).splitlines() if not line.startswith(b'--'))+b'\n'
    outputs={SERVER:server,FRONTEND:g.pretty(catalogues),SQL:sql}
    inputs={n:c.sha(v) for n,v in raw.items()}
    outputs[MANIFEST]=g.pretty(dict(formatVersion=1,targetSchema=25,catalogKey='rackclick-batch50b',state=STATE,inputs=inputs,files={n:c.sha(v) for n,v in outputs.items()},definitions=pins))
    outputs[TARGETS]=b.targets_source({**inputs,**{n:c.sha(v) for n,v in outputs.items()}}).replace(b'Name="VerifyBatch50HardwareCatalog"',b'Name="VerifyBatch50BHardwareCatalog"',1).replace(b'_Batch50',b'_Batch50B').replace(b'batch50_',b'batch50b_').replace(b'<!-- Auto-generated by tools/build_hardware_batch50.py. -->',b'<!-- Auto-generated by tools/build_hardware_batch50b.py. -->',1)
    return outputs

def run(root,write=False):
    # Reuse the reviewed staged-output writer, with this process's isolated compiler.
    b.compile_catalog=compile_catalog
    result=b.run(root,write);result['targetSchema']=25
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);m=p.add_mutually_exclusive_group(required=True);m.add_argument('--write',action='store_true');m.add_argument('--check',action='store_true');a=p.parse_args()
    try:print(json.dumps(run(ROOT,a.write)));return 0
    except (c.CatalogError,OSError) as e:print(json.dumps(dict(status='failed',code=str(e) if isinstance(e,c.CatalogError) else 'batch50b_io_failed')));return 1
if __name__=='__main__':sys.exit(main())
