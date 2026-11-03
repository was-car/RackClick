"""Plan invariants; no PostgreSQL, network, VM, runtime or credentials are used."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('rackclick_demo50_plan', ROOT/'tools/build_demo50_plan.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class Demo50PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.definitions = demo.load_definitions(ROOT)
        cls.plan = demo.build_plan(cls.definitions)

    def test_selected_current_catalogue_and_all_revisions_have_exact_primary_coverage(self):
        plan = self.plan
        self.assertEqual(868, plan['catalogCount'])
        self.assertEqual(862, sum(bool(x['identity']['manufacturer']) for x in plan['catalog']))
        self.assertEqual(861, len({x['profileKey'] for x in plan['catalog'] if x['identity']['manufacturer']}))
        pairs = Counter((x['profileKey'], x['profileVersion']) for c in plan['customers'] for x in c['assignments'])
        self.assertEqual({(x['key'], x['revision']) for x in self.definitions}, set(pairs))
        self.assertEqual({1}, set(pairs.values()))
        self.assertEqual(16928, sum(x['portCount'] for x in plan['catalog']))
        self.assertEqual(2366, sum(x['groupCount'] for x in plan['catalog']))
        self.assertEqual(24, sum(x['connectionApplicability'] == 'not_applicable' for c in plan['customers'] for x in c['assignments']))

    def test_fifty_distinct_customers_and_seven_actual_infrastructure_patterns(self):
        customers = self.plan['customers']
        self.assertEqual(50, len(customers))
        self.assertEqual({'office':10,'medium':10,'multisite':8,'education':6,'industrial':6,'datacenter':6,'mixed':4}, dict(Counter(c['scenario'] for c in customers)))
        self.assertEqual(50, len({c['name'] for c in customers}))
        self.assertEqual({'es','de','en'}, {c['language'] for c in customers})
        self.assertTrue(all(c['assignments'] and c['roomObjects'] for c in customers))
        self.assertTrue(all(len(c['sites']) >= 2 for c in customers if c['scenario']=='multisite'))
        self.assertTrue(all(c['businessRoomKey'] != c['catalogueRoomKey'] for c in customers))

    def test_each_of_88_buildings_has_a_real_business_switch_and_chain_links(self):
        customers = self.plan['customers']
        buildings = [b for c in customers for s in c['sites'] for b in s['buildings']]
        self.assertEqual(88, len(buildings))
        self.assertEqual(88, sum(len(c['businessDevices']) for c in customers))
        self.assertEqual(38, sum(len(c['interBuildingLinks']) for c in customers))
        intersite = 0
        for customer in customers:
            own = {device['key']: device for device in customer['businessDevices']}
            self.assertEqual({b['key']+'.businessswitch' for s in customer['sites'] for b in s['buildings']}, set(own))
            for link in customer['interBuildingLinks']:
                self.assertEqual(demo.BUSINESS_LINK_NOTE, link['note'])
                a, b = own[link['fromDeviceKey']], own[link['toDeviceKey']]
                intersite += a['roomKey'].split('.b')[0] != b['roomKey'].split('.b')[0]
            for device in own.values():
                rack = next(r for r in customer['racks'] if r['key']==device['rackKey'])
                self.assertFalse(rack['catalogueShowcase'])
                self.assertNotEqual(customer['catalogueRoomKey'], rack['roomKey'])
                self.assertEqual(1, rack['reservedUnits'])
                self.assertIn(rack['sizeU'], {6,12,24})
        self.assertEqual(16, intersite)

    def test_removing_business_switch_or_moving_it_to_another_building_is_rejected(self):
        for mutate in ('remove','move'):
            plan = deepcopy(self.plan); customer = next(c for c in plan['customers'] if len(c['businessDevices'])>1)
            if mutate=='remove':
                customer['businessDevices'].pop()
            else:
                customer['businessDevices'][1]['roomKey'] = customer['businessDevices'][0]['roomKey']
            with self.assertRaisesRegex(ValueError, 'plan_building_without_business_switch|plan_business_building_reference_invalid'):
                demo.validate_plan(plan,self.definitions)

    def test_interbuilding_chain_rejects_missing_cross_customer_or_duplicate_links(self):
        for mutate in ('remove','foreign','duplicate'):
            plan=deepcopy(self.plan); customer=next(c for c in plan['customers'] if len(c['interBuildingLinks'])>1)
            if mutate=='remove':
                customer['interBuildingLinks'].pop()
            elif mutate=='foreign':
                customer['interBuildingLinks'][0]['toDeviceKey']=plan['customers'][0]['businessDevices'][0]['key']
            else:
                customer['interBuildingLinks'][1]=deepcopy(customer['interBuildingLinks'][0])
            with self.assertRaisesRegex(ValueError,'plan_interbuilding_chain_invalid'):
                demo.validate_plan(plan,self.definitions)

    def test_same_seed_reordered_input_is_byte_identical_without_mutating_caller(self):
        before = deepcopy(self.definitions)
        rebuilt = demo.build_plan(list(reversed(self.definitions)))
        self.assertEqual(demo.plan_bytes(self.plan), demo.plan_bytes(rebuilt))
        self.assertEqual(before, self.definitions)

    def test_different_seed_changes_placement_without_changing_catalogue_or_scope(self):
        other = demo.build_plan(self.definitions, 'different-demo-seed')
        self.assertEqual(self.plan['catalog'], other['catalog'])
        self.assertEqual(self.plan['catalogDigest'], other['catalogDigest'])
        self.assertNotEqual(self.plan['customers'], other['customers'])
        self.assertFalse(other['securityIncluded'])
        self.assertFalse(other['productionDefault'])

    def test_duplicate_profile_revision_is_rejected_even_when_total_is_868(self):
        rows = deepcopy(self.definitions); rows[1] = deepcopy(rows[0])
        with self.assertRaisesRegex(ValueError, 'duplicate_profile_revision'):
            demo.build_plan(rows)

    def test_authoring_reader_cannot_silently_mix_a_pin_from_another_checkout(self):
        module = demo.importlib.import_module('test_hardware_selected506l')
        current, baseline, receiver, pins = module.authoring()
        pins = dict(pins); pins['AGENTS.md'] = '0'*64
        with mock.patch.object(module, 'authoring', return_value=(current, baseline, receiver, pins)):
            with self.assertRaisesRegex(ValueError, 'authoring_source_pin_mismatch'):
                demo.load_definitions(ROOT)

    def test_dc_without_system_or_role_is_not_silently_turned_into_ac_or_unspecified(self):
        for field in ('powerSystem','powerRole'):
            rows = deepcopy(self.definitions)
            group = next(g for row in rows for g in row['groups'] if g['type']=='power_dc')
            group.pop(field)
            with self.assertRaisesRegex(ValueError, 'dc_role_or_system_invalid'):
                demo.build_plan(rows)

    def test_unknown_mount_and_desktop_without_real_shelf_fit_are_rejected(self):
        rows = deepcopy(self.definitions); rows[0]['kind'] = 'invented'
        with self.assertRaisesRegex(ValueError, 'unsupported_mount_kind'):
            demo.build_plan(rows)
        rows = deepcopy(self.definitions)
        next(row for row in rows if row['kind']=='desktop')['dimensionsMm']['width'] = 10000
        with self.assertRaisesRegex(ValueError, 'approved_shelf_fit_unavailable'):
            demo.build_plan(rows)

    def test_cross_customer_room_and_unknown_rack_reference_are_rejected(self):
        for field in ('roomKey','rackKey'):
            plan = deepcopy(self.plan)
            item = next(x for x in plan['customers'][0]['assignments'] if 'rackKey' in x)
            item[field] = plan['customers'][1]['catalogueRoomKey'] if field=='roomKey' else 'missing-rack'
            with self.assertRaisesRegex(ValueError, 'reference_invalid'):
                demo.validate_plan(plan, self.definitions)

    def test_missing_primary_assignment_and_overfull_rack_are_rejected(self):
        plan = deepcopy(self.plan); plan['customers'][0]['assignments'].pop()
        with self.assertRaises(ValueError):
            demo.validate_plan(plan, self.definitions)
        plan = deepcopy(self.plan); plan['customers'][0]['racks'][0]['reservedUnits'] = 10000
        with self.assertRaisesRegex(ValueError, 'rack_capacity_invalid'):
            demo.validate_plan(plan, self.definitions)

    def test_materialized_profile_is_not_relabelled_as_not_applicable(self):
        plan = deepcopy(self.plan)
        item = next(x for c in plan['customers'] for x in c['assignments'] if x['connectionApplicability']=='required')
        item['connectionApplicability'] = 'not_applicable'
        with self.assertRaisesRegex(ValueError, 'connection_applicability_invalid'):
            demo.validate_plan(plan, self.definitions)

    def test_secret_fields_or_production_default_are_rejected(self):
        plan = deepcopy(self.plan); plan['customers'][0]['credentials'] = {'password':'synthetic-unusable-fixture'}
        with self.assertRaisesRegex(ValueError, 'contains_security_fields'):
            demo.validate_plan(plan, self.definitions)
        plan = deepcopy(self.plan); plan['productionDefault'] = True
        with self.assertRaisesRegex(ValueError, 'security_or_production_scope_invalid'):
            demo.validate_plan(plan, self.definitions)

    def test_multisite_cannot_be_relabeled_without_its_multiple_sites(self):
        plan = deepcopy(self.plan)
        customer = next(c for c in plan['customers'] if c['scenario']=='multisite')
        customer['sites'] = customer['sites'][:1]
        with self.assertRaisesRegex(ValueError, 'multisite_requires_multiple_sites'):
            demo.validate_plan(plan, self.definitions)

    def test_file_creation_is_exclusive_check_is_read_only_and_tampering_fails(self):
        with tempfile.TemporaryDirectory(prefix='rackclick-demo50-plan-') as directory:
            target = Path(directory)/'plan.json'
            self.assertEqual(0, demo.main(['--output',str(target)]))
            original = target.read_bytes()
            with self.assertRaises(FileExistsError):
                demo.main(['--output',str(target)])
            self.assertEqual(original,target.read_bytes())
            self.assertEqual(0, demo.main(['--output',str(target),'--check']))
            self.assertEqual(original,target.read_bytes())
            value=json.loads(original);value['customers'][0]['name']='Tampered synthetic name'
            target.write_bytes(demo.plan_bytes(value))
            with self.assertRaisesRegex(ValueError,'not_reproducible'):
                demo.main(['--output',str(target),'--check'])


if __name__=='__main__':
    unittest.main()
