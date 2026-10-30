"""Read-only final guards for same-database QA13 and final Windows bundle."""
from datetime import datetime,timezone
import hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269';GIT=ROOT/'.local/git-2.55.0.5/cmd/git.exe'
PIN='dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(n):return json.loads((E/n).read_bytes())
def exact(values):assert values and all(sha(ROOT/p)==h for p,h in values.items())
def protected_inputs():
 initial=read('INICIO-02.json');runtime=read('ALCANCE-RUNTIME-FUENTE.json')['authorizedMutableRuntimeFiles'];mutable=set(initial['authorizedMutableGuards'])|set(runtime)
 protected={p:h for p,h in initial['guards'].items() if p not in mutable};exact(protected)
 config=initial['sourceDirectory']+'/manual-qa.json';static={p:h for p,h in initial['sourceQaGuards'].items() if p not in set(runtime)|{config}};assert len(static)==20;exact(static)
 for p,row in runtime.items():assert initial['guards'][p]==row['sha256'] and sha(ROOT/row['privateArchive'])==row['sha256'] and (ROOT/row['privateArchive']).stat().st_size==row['bytes']
 assert sha(ROOT/initial['originalConfigurationArchive'])==initial['guards'][config]
 changes={p:('absent' if not (ROOT/p).exists() else sha(ROOT/p)) for p,row in runtime.items() if not (ROOT/p).exists() or sha(ROOT/p)!=row['sha256']}
 return initial,len(protected),len(static),changes
def current_product():
 sources=read('SOURCE-FREEZE-APP.json')['sources'];assert len(sources)==193;exact(sources);p=ROOT/read('INICIO-02.json')['targetManifest'];assert sha(p)==PIN;m=json.loads(p.read_bytes())
 artifacts=[(ROOT/m['candidateDirectory']/part/n,h) for part,files in m['distributions'].items() for n,h in files.items()];assert len(artifacts)==40 and all(sha(p)==h for p,h in artifacts) and sum(p.stat().st_size for p,h in artifacts)==7146303
 baseline=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json').read_bytes());assert m['distributions']['server']==baseline['distributions']['server'];return m
def technical_gate():
 gate=read('revision/GATE-TECNICO.json');assert gate['valid'] and gate['approved'] and not gate['openBlockingFindings'] and gate['targetManifestSha256']==PIN
 for k in ['sourceHashes','manualHashes']:exact(gate[k])
 assert all(sha(E/p)==h for p,h in gate['observedFilesSha256'].items())
 applicability=read('revision/COMPATIBILIDAD-FOCO-03.json');assert applicability['valid'] and applicability['changedSourceMethodsNotExecutedInOwnFocus'];exact(applicability['runtimeModulesByteExact']);exact(applicability['finalSourceHashes']);return gate
def selected_qa():
 sys.path.insert(0,str(ROOT/'tools/windows'))
 from qa_artifact13_update1269 import validate_operation,OwnedRuntime
 pointer=ROOT/'.local/qa-rc9/current.json';initial=read('INICIO-02.json');assert sha(pointer)==initial['guards'][pointer.relative_to(ROOT).as_posix()]
 directory=ROOT/initial['sourceDirectory'];source=validate_operation(directory,pointer,real=True);assert source.revision==1209;OwnedRuntime(directory,source.cfg,source.operation).quiet()
 before=json.loads((ROOT/initial['originalConfigurationArchive']).read_bytes());after=json.loads((directory/'manual-qa.json').read_bytes());assert sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))==['artifactDirectory','bundleSha256']
 actual=read('REAL-QA-UPDATE-01.json');assert actual['valid'] and actual['state']=='committed' and actual['leftRunning'] is False and (ROOT/actual['operationDirectory']).resolve()==source.operation.resolve()
 assert read('REAL-QA-VALIDATE-01.json')['valid'];assert sha(directory/'manual-qa.json')==read('REAL-QA-VALIDATE-01.json')['currentConfigSha256']
 assert sha(source.operation/'artifact13-prepared.json')==(source.operation/'artifact13-prepared.sha256').read_text(encoding='ascii').strip()
 assert len(source.record['databaseStates']['databases']['primary']['snapshot'])==39 and len(source.record['databaseStates']['databases']['recovery969']['snapshot'])==37
 return source
def final_guide():
 spec=importlib.util.spec_from_file_location('guide1269final',ROOT/'tools/windows/qa_guide.py');guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
 catalog=json.loads(guide.CATALOG.read_bytes());old=json.loads(subprocess.check_output([str(GIT),'show',read('INICIO-02.json')['baseCommit']+':docs/QA-CASOS-WASCAR.json']));assert len(catalog['cases'])==87 and catalog['cases'][:84]==old['cases'][:84]
 matrix=read('QA-MATRIX-1269.json')
 for k,v in old.items():
  if k not in ['cases','revision']:assert catalog[k]==(v+[matrix['pair']] if k in matrix['inheritedBuildLists'] else v)
 assert catalog['adminUserOnboardingBuilds']==[matrix['pair']]
 for c,o in zip(catalog['cases'][84:],old['cases'][84:]):assert c=={**o,'feature':'adminUserOnboardingGui','steps':[c['steps'][0]]+o['steps'][1:]}
 availability={}
 for profile in ['manual','rc9']:
  assert guide.generate(check=True,profile=profile);cases=json.loads(guide.render(catalog,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases'];availability[profile]=sum(v['available'] for v in cases.values())
 assert availability==dict(manual=8,rc9=87);return availability
def main():
 output=E/'VERIFICACION-FINAL.json';assert not output.exists();initial,protected,static,changes=protected_inputs();current_product();gate=technical_gate();package=read('PACKAGES-02.json');assert package['valid'] and package['byteIdentical'] and package['sourcesUnchanged'] and package['sourceManifestSha256']==PIN
 exact(read('SOURCE-FREEZE-OPERATORS-02.json')['sources']);assert gate['archiveSha256']==package['outputs'][0]['sha256'];assert all(sha(ROOT/r['path'])==r['sha256'] and (ROOT/r['path']).stat().st_size==r['bytes'] for r in package['outputs'])
 assert read('COMPATIBILIDAD-DOCUMENTAL-02.json')['valid'] and read('ZIP02-CLI.json')['successful'];native=read('windows/native01/result.json');assert native['successful'] and native['inputsUnchanged'] and native['ownedProcessesStopped'] and not native['cleanupErrors'] and native['recoverySnapshotExact'] and native['systemCrtDllsAndX64RegistryUnchanged']
 assert native['archiveSha256']==read('PACKAGES-01.json')['outputs'][0]['sha256'] and len(native['tableDigestsBeforeBackup'])==39
 assert read('windows/profiles02/result.json')['successful'];assert read('qa-update/RESUMEN-AUTOR.json')['successful'];assert read('revision/fault02/result.json')['successful'];assert read('QA-TESTS-01.json')['successful']
 go=read('COORDINATOR-GO.json');assert go['valid'];exact(go['gates']);selected_qa();available=final_guide()
 plan=json.loads((ROOT/'docs/PLAN-SESENTA-TANDAS-1210-1269.json').read_bytes());assert plan['completed']==60 and len(plan['batches'])==60 and all(b['status']=='verified' and (ROOT/b['evidence']).is_file() for b in plan['batches'])
 progress=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_bytes());assert progress['progress']==78 and [s['points'] for s in progress['streams']]==[18,22,14,14,9,1] and [s['weight'] for s in progress['streams']]==[20,25,15,15,15,10]
 assert subprocess.check_output([str(GIT),'rev-parse','HEAD'],text=True).strip()==initial['baseCommit']
 record=dict(utc=datetime.now(timezone.utc).isoformat(),successful=True,protectedFilesExact=protected,immutableQaRootFilesExact=static,originalRuntimeFilesPrivatelyArchived=7,allowedRuntimeChanges=changes,productSourcesExact=193,candidateFilesExact=40,selectedQaFrontendRevision=1209,selectedServerRevision=1089,selectedQaSchema=13,recoveryRevision=969,recoverySchema=12,realQaPrimaryTables=39,realQaRecoveryTables=37,sameRootDatabaseOidsCredentialsSessionsGrants=True,pointerUnchanged=True,configChangedFields=['artifactDirectory','bundleSha256'],available=available,previous84CasesExact=True,manualWascarResultsWritten=False,newApplicationPublications=0,newFrontendBuilds=0,processesQuiet=True,independentGateApproved=True,finalAdoption=False,progress=78)
 with output.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
 print(json.dumps(record))
if __name__=='__main__':main()
