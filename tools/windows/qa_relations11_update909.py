"""Closed832/11->849/11 CLI. Real use follows separate operational GO."""
import argparse
import json
from pathlib import Path
import sys

from qa_relations11_source909 import Schema11Error
from qa_relations11_switch909 import prepare_operation, validate_operation, activate, rollback, worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'validate', 'activate', 'rollback', '_supervise', '_worker'))
    parser.add_argument('--source', type=Path)
    parser.add_argument('--pointer', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--real-restored', action='store_true')
    parser.add_argument('--selected', action='store_true', help='Static validation of selected849 pointer only')
    parser.add_argument('--preview', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.action in ('_worker', '_supervise'):
            if args.candidate is None or args.source is not None or args.pointer is not None or args.real_restored or args.selected:
                raise Schema11Error('internal909_worker_arguments_invalid')
            worker(args.candidate, supervise=args.action == '_supervise', preview=args.preview)
            return 0
        if args.source is None or args.pointer is None:
            raise Schema11Error('explicit909_source_and_pointer_required')
        if args.preview or args.selected and args.action != 'validate':
            raise Schema11Error('public909_arguments_invalid')
        if args.action == 'prepare':
            if args.candidate is not None:
                raise Schema11Error('prepare909_always_allocates_new_candidate')
            result = prepare_operation(args.source, args.pointer, real=args.real_restored)
            print(json.dumps({'state': result.state, 'candidateDirectory': str(result.candidate.directory),
                              'sourceSchema': 11, 'candidateSchema': 11, 'selectedSchema': 11,
                              'sourceRevision': 832, 'candidateRevision': 849, 'selectedRevision': 832,
                              'leftRunning': False, 'activationConfirmed': False}))
        else:
            if args.candidate is None:
                raise Schema11Error('explicit909_prepared_candidate_required')
            if args.action == 'validate':
                validate_operation(args.source, args.pointer, args.candidate, real=args.real_restored, selected=args.selected)
                print(json.dumps({'state': 'static_validated', 'sourceSchema': 11, 'candidateSchema': 11,
                                  'selectedSchema': 11, 'sourceRevision': 832, 'candidateRevision': 849,
                                  'selectedRevision': 849 if args.selected else 832, 'databaseTestExecuted': False}))
            else:
                operation = activate if args.action == 'activate' else rollback
                result = operation(args.source, args.pointer, args.candidate, real=args.real_restored)
                print(json.dumps({'state': result.state, 'sourceSchema': 11, 'candidateSchema': 11,
                                  'selectedSchema': 11, 'sourceRevision': 832, 'candidateRevision': 849,
                                  'selectedRevision': 849 if result.state == 'committed' else 832, 'leftRunning': False,
                                  'activationConfirmed': result.state == 'committed'}))
        return 0
    except Exception as error:
        print(json.dumps({'state': getattr(error, 'code', 'closed909_validation_failed'),
                          'selectedSchema': None, 'selectedRevision': None, 'activationConfirmed': False,
                          'leftRunning': None}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
