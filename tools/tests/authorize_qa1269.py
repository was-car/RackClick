"""Require concrete independent gates before actual artifact-only QA update."""
from datetime import datetime,timezone
import ast,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269';PIN='dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b'
sys.path.insert(0,str(ROOT/'tools/windows'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def exact(d):assert d and all(sha(ROOT/p)==h for p,h in d.items())
def main():
 from qa_artifact13_source1269 import Source13
 from qa_artifact13_update1269 import OwnedRuntime
 out=E/'COORDINATOR-GO.json';assert not out.exists()
 names=['PACKAGES-02.json','SOURCE-FREEZE-OPERATORS-02.json','COMPATIBILIDAD-DOCUMENTAL-02.json','ZIP02-CLI.json','windows/profiles02/result.json','windows/native01/result.json','qa-update/RESUMEN-AUTOR.json','qa-update/run03/result.json','revision/fault02/result.json','revision/GATE-TECNICO.json','REAL-QA-PREFLIGHT-01.json','qa-update/run01/result.json','revision/COMPATIBILIDAD-FOCO-03.json','qa-update/run02/result.json']
 records={n:read(E/n) for n in names};exact(read(E/'SOURCE-FREEZE-APP.json')['sources']);assert len(read(E/'SOURCE-FREEZE-APP.json')['sources'])==193
 assert sha(ROOT/'evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json')==PIN
 package=records[names[0]];assert package['valid'] and package['byteIdentical'] and package['sourcesUnchanged'] and package['sourceManifestSha256']==PIN;exact(records[names[1]]['sources']);assert all(sha(ROOT/r['path'])==r['sha256'] for r in package['outputs'])
 compat=records[names[2]];assert compat['valid'] and compat['applicationFilesExact']==40 and compat['operatorsExact']==25 and not compat['nativeNewRestoreRerun'];assert compat['finalArchiveSha256']==package['outputs'][0]['sha256'];assert records[names[3]]['successful']
 profiles=records[names[4]];assert profiles['successful'] and profiles['testsRun']==3
 native=records[names[5]];assert native['successful'] and native['testsRun']==1 and native['archiveSha256']==compat['testedNativeArchiveSha256'] and native['applicationManifestSha256']==PIN
 assert all(native[k] for k in ['inputsUnchanged','ownedProcessesStopped','systemCrtDllsAndX64RegistryUnchanged','recoverySnapshotExact']) and not native['cleanupErrors'] and native['successfulOperationalRecoveries']==1
 assert len(native['tableDigestsBeforeBackup'])==39 and len(native['frontendTransportChecks'])==2 and all(r['httpServedAppJsExact'] and not r['domExecuted'] for r in native['frontendTransportChecks'])
 installed=native['onboardingChecks'][0];assert all(installed[k] for k in ['newAccountInitiallyUngroupedAndNoCapabilities','grantAloneDoesNotAssignMembership','membershipTargetsExactUuidAmongHomonyms','secondAdminSessionReadsCommittedGroupAndEffectiveSources','onlyAssignedCustomerVisible','readerAdmin403AndWrite403'])
 assert native['recoveryChecks'][0]['originalAccountsCredentialsMembershipsGrantsAndEffectivePermissionsPreserved'] and native['recoveryChecks'][0]['copiedSessionsRevoked']
 failed=records[names[11]];assert not failed['successful'] and failed['testsRun']==5
 contracts02=records[names[13]];assert not contracts02['successful'] and contracts02['testsRun']==6 and contracts02['inputsUnchanged']
 passed=[r for r in contracts02['cases'] if '.Closed1269Contracts.' in r['test']];assert len(passed)==5 and all(r['status']=='passed' for r in passed)
 testpath='development/server/tests/test_qa_artifact13_update1269.py';oldtest=E/'qa-update/run02/sources'/testpath;assert sha(oldtest)==contracts02['sourceHashes'][testpath]
 def contract_ast(p):return ast.dump(next(n for n in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(n,ast.ClassDef) and n.name=='Closed1269Contracts'),include_attributes=False)
 assert contract_ast(oldtest)==contract_ast(ROOT/testpath)
 exact({p:h for p,h in contracts02['sourceHashes'].items() if p!=testpath})
 author,run=records[names[6]],records[names[7]];assert author['successful'] and run['successful'] and run['testsRun']==1 and run['inputsUnchanged'];exact(run['sourceHashes']);assert len(run['labs'])==5 and all(all(row.values()) for row in run['labs'])
 observation=run['observations'][0];assert all(observation[k] for k in ['genuinePrepared1149Fixture','originalPrepared1149SealExact','post1149LegitimateDataAccepted','onlyTwoConfigFieldsChanged','sameDatabaseOidsHistoriesGrantsAndPrivateInputs','quietAfterConfigFailureRolledBack','committedSuccess','idempotentReentryWithoutNewBaseline','originalSessionAndCategory13ReceiptRetained']) and observation['baselineRenewals']==0
 own=records[names[8]];assert own['successful'] and own['testsRun']==1 and not own['postgresqlExecuted'] and own['inputsUnchanged'] and own['observations']['priorSelectionPreserved'] and own['observations']['baselineAndRecordUnchanged']
 applicability=records[names[12]];assert applicability['valid'] and applicability['changedSourceMethodsNotExecutedInOwnFocus'] and not applicability['fullFinalSource13ValidationClaimed'];exact(applicability['runtimeModulesByteExact']);exact(applicability['finalSourceHashes'])
 gate=records[names[9]];assert gate['valid'] and gate['approved'] and not gate['openBlockingFindings'] and gate['targetManifestSha256']==PIN and gate['archiveSha256']==package['outputs'][0]['sha256']
 for k in ['sourceHashes','manualHashes']:exact(gate[k])
 assert all(sha(E/p)==h for p,h in gate['observedFilesSha256'].items())
 pre=records[names[10]];assert pre['valid'] and pre['sourceQuiet'] and not pre['postgresqlStarted'];pointer=ROOT/'.local/qa-rc9/current.json';source=Source13(ROOT/pre['directory'],pointer,real=True);OwnedRuntime(source.directory,source.cfg).quiet();assert source.revision==1089 and source.hashes==pre['sourceInputHashes'] and sha(pointer)==pre['pointerSha256'] and sha(source.directory/'manual-qa.json')==pre['sourceConfigSha256']
 record=dict(utc=datetime.now(timezone.utc).isoformat(),valid=True,authorizedRealQaArtifactUpdate=True,sourceQuietReconfirmed=True,sourceInputsExact=True,gates={(E/n).relative_to(ROOT).as_posix():sha(E/n) for n in names},scope='Existing S1 authorization. Artifact-only1209 in same1149 root/primary13/recovery96912; no migration/new DB/grants/secrets/login/applicationDML. Both current logical states and immutable activity baseline guarded.',contracts02Passed=5,contractsClassAstExact03=True,contracts02WholeRunStillFailed=True,native03Passed=1,applicationBuilds=0,frontendBuilds=0,manualWascarResultsWritten=False,finalAdoption=False)
 with out.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
 print(json.dumps(dict(valid=True,gates=len(names),sourceQuietReconfirmed=True,finalAdoption=False)))
if __name__=='__main__':main()
