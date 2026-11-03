"""A sealed hardware inlet cannot be turned into an outlet through ports.update."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback

from pg_support import Lab, protect_directory
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import state
from test_hardware_batch100c import BatchSession, create_racks

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to((ROOT/'.local').resolve()) and not out.exists()
    out.mkdir(parents=True)
    protect_directory(out)
    result = dict(result='FAIL', code='not_run', serverSha256=hashlib.sha256(args.dll.read_bytes()).hexdigest())
    lab = None
    try:
        lab = Lab('hardware-fixed-power-role')
        with lab:
            db = lab.create_database('fixed-role')
            ids, password = fixture(lab, db, args.dll)
            rack_fixture = create_racks(lab, db, ids, ['Fixed hardware role'], pdu=True)[0]
            rack = rack_fixture['rack']
            lab.grant_runtime(db)
            server = lab.start_server(db, dll=args.dll)
            session = BatchSession(server, ids, password)
            request = dict(profileKey='aruba-jl682a', profileVersion='aruba-20261030-v1', rackId=rack, name='Fixed inlet')
            device = session.send(request).json()['result']['resourceId']
            project = session.project()
            inlet = next(p for p in project['ports'] if p['deviceId'] == device and p['type'] == 'power')
            group = next(g for g in project['portGroups'] if g['id'] == inlet['groupId'])
            before = state(lab, db)
            patch = dict(deviceId=device, groupId=group['id'], groupType='power', portIds=[inlet['id']], changes={'powerRole':'outlet'})
            response = session.send(patch, kind='ports.update', status=422)
            assert response.json()['error'] == 'hardware_metadata_immutable'
            assert state(lab, db) == before
            unchanged = patch|dict(changes={'powerRole':'inlet', 'label':'Known inlet'})
            assert session.send(unchanged, kind='ports.update').status == 200
            project = session.project()
            final = next(p for p in project['ports'] if p['id'] == inlet['id'])
            assert final['powerRole'] == 'inlet' and final['label'] == 'Known inlet'
            generic = next(p for p in project['ports'] if p['id'] == rack_fixture['pduPortId'])
            generic_patch = dict(deviceId=generic['deviceId'], groupId=generic['groupId'], groupType='power',
                                 portIds=[generic['id']], changes={'powerRole':'inlet'})
            assert session.send(generic_patch, kind='ports.update').status == 200
            result.update(result='PASS', code='fixed_role_preserved', rejectedWithoutMutation=True,
                          sameRoleMetadataAllowed=True, genericRoleStillEditable=True)
    except BaseException as error:
        result.update(result='FAIL', code='assertion_failed', failureType=type(error).__name__)
        (out/'runner-private.log').write_text(traceback.format_exc(), encoding='utf-8')
    finally:
        result.update(labStopped=lab is None or not lab.running,
                      serversStopped=lab is None or all(s.process.poll() is not None for s in lab.servers))
        (out/'RESULTADOS.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(result))
    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
