"""Isolated F-05.05 integration run; never accepts existing database credentials or a VM.

The project must reference the reviewed product DLL from its own private build.
Raw test output, credentials, archives and binlogs remain under .local.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import Lab, NO_WINDOW, protect_directory


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--fixture-root',type=Path,required=True)
    parser.add_argument('--result',type=Path,required=True)
    args=parser.parse_args()
    project=args.project.resolve();fixture=args.fixture_root.resolve();result=args.result.resolve()
    private=ROOT/'.local'
    if (not project.is_relative_to(private) or not fixture.is_relative_to(private) or
        not project.is_file() or not fixture.is_dir() or result.exists() or
        not result.is_relative_to(ROOT/'evidence/s1-20261103/f05-05-cierre')):
        raise RuntimeError('scope_invalid')
    for path in (project,fixture):
        for node in (path,*path.parents):
            if node.exists() and node.is_junction():raise RuntimeError('reparse_rejected')
    lab=Lab('f0505-application-restore')
    logs=lab.directory/'test-results';logs.mkdir();protect_directory(logs)
    private_receipt=fixture/('runner-private-'+uuid.uuid4().hex+'.json')
    with private_receipt.open('x',encoding='utf-8') as stream:
        json.dump(dict(labDirectory=str(lab.directory),testResults=str(logs),fixtureRoot=str(fixture),project=str(project)),stream,indent=2)
    outcome=dict(schemaVersion=1,valid=False,scope='new_application_databases_and_in_memory_Program_pipeline',
                 VMOperations=0,DGuestCommands=0,installedStoresChanged=0,
                 adoptedDatabase=False,productOperatorClaimed=False)
    environment=lab.environment
    def clean_env():
        env=environment()
        for name in list(env):
            if name.upper().startswith(('PG','DOTNET_','CORECLR_','COR_','COMPLUS_','ASPNETCORE_','CONNECTIONSTRINGS','SQLSECRET','MFAKEYSTORE','RACKCLICK_TEST_')) or name.upper() in ('STARTUPHOOKS','STARTUP_HOOKS'):
                del env[name]
        env['PGCLIENTENCODING']='UTF8';env['PYTHONIOENCODING']='utf-8'
        env['DOTNET_EnableDiagnostics']='0'
        env['DOTNET_ROOT']=str(lab.dotnet.parent)
        env['DOTNET_ROOT_X64']=str(lab.dotnet.parent)
        env['DOTNET_HOST_PATH']=str(lab.dotnet)
        env['DOTNET_CLI_HOME']=str(ROOT/'.local/dotnet-home')
        env['DOTNET_CLI_TELEMETRY_OPTOUT']='1';env['DOTNET_NOLOGO']='1'
        env['DOTNET_GENERATE_ASPNET_CERTIFICATE']='false'
        env['DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE']='1'
        return env
    lab.environment=clean_env
    try:
        lab.start()
        env=lab.environment()
        env['RACKCLICK_TEST_PG_ADMIN']=f'Host=127.0.0.1;Port={lab.port};Database=postgres;Username={lab.admin};Password={lab.admin_password};Pooling=false'
        env['RACKCLICK_TEST_PG_BIN']=str(lab.pg_bin)
        env['RACKCLICK_TEST_F0505_ROOT']=str(fixture)
        env['NUGET_PACKAGES']=str(ROOT/'.local/nuget/packages')
        command=[str(lab.dotnet),'test',str(project),'--no-build','--no-restore','-c','Release',
                 '--logger','trx;LogFileName=f0505.trx','--results-directory',str(logs),
                 '--filter','FullyQualifiedName~MfaPortableDatabaseRestoreTests',
                 '-bl:'+str(lab.directory/'test-{}.binlog')]
        with (logs/'stdout-private.txt').open('xb') as stdout,(logs/'stderr-private.txt').open('xb') as stderr:
            run=subprocess.run(command,stdout=stdout,stderr=stderr,stdin=subprocess.DEVNULL,cwd=ROOT,
                               env=env,timeout=600,creationflags=NO_WINDOW)
        outcome['testExitCode']=run.returncode
        report=logs/'f0505.trx'
        if report.exists():
            tree=ET.parse(report);ns={'t':'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
            counters=tree.find('.//t:ResultSummary/t:Counters',ns)
            if counters is not None:
                outcome['counters']={k:int(v) for k,v in counters.attrib.items()}
            outcome['cases']=[dict(name=node.attrib['testName'],outcome=node.attrib['outcome']) for node in tree.findall('.//t:UnitTestResult',ns)]
        outcome['valid']=(run.returncode==0 and outcome.get('counters',{}).get('total',0)>0 and
                          outcome['counters'].get('failed',1)==0 and
                          outcome['counters'].get('passed')==outcome['counters']['total'])
        outcome['testBinlogProduced']=len(list(lab.directory.glob('test-*.binlog')))>0
    finally:
        lab.close()
        outcome['ownClusterStopped']=not lab.running
        result.parent.mkdir(parents=True,exist_ok=True)
        result.write_text(json.dumps(outcome,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(outcome))
    return 0 if outcome['valid'] and outcome['testBinlogProduced'] and outcome['ownClusterStopped'] else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        print(json.dumps(dict(valid=False,code='isolated_integration_failed_preserved',exceptionType=type(error).__name__)))
        raise SystemExit(1) from None
