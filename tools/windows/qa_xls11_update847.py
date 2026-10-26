"""Closed712/11->832-02/11 CLI. Real use follows separate operational GO."""
import argparse
import json
from pathlib import Path
import sys

from qa_xls11_source847 import Schema11Error
from qa_xls11_switch847 import prepare_operation, validate_operation, activate, rollback, worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'validate', 'activate', 'rollback', '_supervise', '_worker'))
    parser.add_argument('--source', type=Path)
    parser.add_argument('--pointer', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--real-restored', action='store_true')
    parser.add_argument('--selected', action='store_true', help='Static validation of selected832 pointer only')
    parser.add_argument('--preview', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.action in ('_worker', '_supervise'):
            if args.candidate is None or args.source is not None or args.pointer is not None or args.real_restored or args.selected:
                raise Schema11Error('internal847_worker_arguments_invalid')
            worker(args.candidate, supervise=args.action == '_supervise', preview=args.preview)
            return 0
        if args.source is None or args.pointer is None:
            raise Schema11Error('explicit847_source_and_pointer_required')
        if args.preview or args.selected and args.action != 'validate':
            raise Schema11Error('public847_arguments_invalid')
        if args.action == 'prepare':
            if args.candidate is not None:
                raise Schema11Error('prepare847_always_allocates_new_candidate')
            result = prepare_operation(args.source, args.pointer, real=args.real_restored)
            print(json.dumps({'state': result.state, 'candidateDirectory': str(result.candidate.directory),
                              'sourceSchema': 11, 'candidateSchema': 11, 'selectedSchema': 11,
                              'sourceRevision': 712, 'candidateRevision': 832, 'selectedRevision': 712,
                              'leftRunning': False, 'activationConfirmed': False}))
        else:
            if args.candidate is None:
                raise Schema11Error('explicit847_prepared_candidate_required')
            if args.action == 'validate':
                validate_operation(args.source, args.pointer, args.candidate, real=args.real_restored, selected=args.selected)
                print(json.dumps({'state': 'static_validated', 'sourceSchema': 11, 'candidateSchema': 11,
                                  'selectedSchema': 11, 'sourceRevision': 712, 'candidateRevision': 832,
                                  'selectedRevision': 832 if args.selected else 712, 'databaseTestExecuted': False}))
            else:
                operation = activate if args.action == 'activate' else rollback
                result = operation(args.source, args.pointer, args.candidate, real=args.real_restored)
                print(json.dumps({'state': result.state, 'sourceSchema': 11, 'candidateSchema': 11,
                                  'selectedSchema': 11, 'sourceRevision': 712, 'candidateRevision': 832,
                                  'selectedRevision': 832 if result.state == 'committed' else 712, 'leftRunning': False,
                                  'activationConfirmed': result.state == 'committed'}))
        return 0
    except Exception as error:
        print(json.dumps({'state': getattr(error, 'code', 'closed847_validation_failed'),
                          'selectedSchema': None, 'selectedRevision': None, 'activationConfirmed': False,
                          'leftRunning': None}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
