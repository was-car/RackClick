"""Exact SQL snapshot and 43->45 migration on a NEW PG17 lab, never VM/SCM.

Preserves synthetic MFA ciphertext, sessions, policy, users and inventory without
claiming that synthetic ciphertext is a valid factor or testing the Windows broker.
"""
import argparse, hashlib, json, subprocess, traceback
from pathlib import Path
from test_hardware_german_cpe import TrialLab
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import migrate, runtime_sql

ROOT=Path(__file__).resolve().parents[3]

def snapshot_sql():
    raw=(ROOT/'tools/windows/server-install/RackClick.ApplicationUpgrade.ps1').read_text(encoding='utf-8')
    return raw.split("return @'\n",1)[1].split("\n'@",1)[0]

def snapshot(lab,db):
    # Match the operator's psql -q: the general Lab helper otherwise emits the
    # CREATE FUNCTION command tag before the single JSON result.
    return json.loads(lab.sql(db,'\\set QUIET 1\n'+snapshot_sql()))

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline-dll',type=Path,required=True);p.add_argument('--dll',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    old=a.baseline_dll.resolve(strict=True);new=a.dll.resolve(strict=True);out=a.output.absolute()
    assert out.is_relative_to((ROOT/'.local').absolute()) and not out.exists();out.mkdir(parents=True)
    result={'result':'FAIL','vmAccessed':False,'servicesChanged':False,'baselineSha256':hashlib.sha256(old.read_bytes()).hexdigest(),'serverSha256':hashlib.sha256(new.read_bytes()).hexdigest()}
    lab=TrialLab('application-upgrade43to45');stage='fixture'
    try:
      with lab:
        db=lab.create_database('application-upgrade43');ids,password=fixture(lab,db,old)
        house,admin=lab.sql(db,"SELECT id FROM systemhaus; SELECT id FROM app_user WHERE username='hardware-admin'").splitlines()
        lab.sql(db,f"""INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required,enrollment_pending,revision) VALUES('{house}','{admin}',true,false,7);
INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version,last_time_step,confirmed_at) VALUES('{house}','{admin}','active',decode(repeat('ab',64),'hex'),1,123,clock_timestamp());
INSERT INTO app_mfa_policy(systemhaus_id,enabled,grace_days,activated_at) VALUES('{house}',true,45,clock_timestamp());
INSERT INTO app_mfa_recovery_code(systemhaus_id,user_id,code_hash) VALUES('{house}','{admin}',repeat('c',64));""",sensitive=True)
        stage='snapshot_before';before=snapshot(lab,db);assert before['migrationCount']==43 and before['catalogueCount']==868
        assert before['tables']['app_mfa_factor']['count']==1 and before['tables']['app_mfa_policy']['count']==1
        stage='migrate';assert migrate(lab,db,new,out/'migrate-private.log')==0
        stage='snapshot_after';after=snapshot(lab,db)
        assert after['migrationCount']==45 and after['catalogueCount']==884
        assert after['tables']==before['tables'] and after['history43']==before['history43']
        lab.grant_runtime(db)
        assert runtime_sql(lab,db,'DELETE FROM hardware_definition').returncode!=0
        assert runtime_sql(lab,db,'CREATE TABLE forbidden_upgrade45(id integer)').returncode!=0
        stage='repeat';assert migrate(lab,db,new,out/'repeat-private.log')==0
        assert snapshot(lab,db)==after
        result.update(result='PASS',schemaBefore=43,schemaAfter=45,catalogueBefore=868,catalogueAfter=884,nonCatalogueTablesUnchanged=len(before['tables']),syntheticMfaFactorPreserved=True,recoveryCodesAndPolicyPreserved=True,history43Unchanged=True,repeatMigrationIdempotent=True,runtimeDDLAndCatalogueDMLDenied=True,postgresql=lab.sql('postgres','SHOW server_version'),windowsBrokerNotExecuted=True)
    except BaseException as error:
        result.update(failureStage=stage,failureType=type(error).__name__);(out/'failure-private.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers))
        (out/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
    return 0 if result['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
