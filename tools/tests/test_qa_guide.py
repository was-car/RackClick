import importlib.util
import json
from pathlib import Path
import unittest
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('qa_guide', ROOT / 'tools/windows/qa_guide.py')
guide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guide)


class GuideTests(unittest.TestCase):
    def test_members_require_matching_frontend_and_server(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        ctx = {'configured': True, 'origin': '', 'bundle': catalog['membersBundle'], 'dll': 'old', 'roles': True}
        def availability():
            rendered = guide.render(catalog, ctx)
            return json.loads(rendered.split('const guide=', 1)[1].split(';', 1)[0])['cases']['QA-12']['available']
        self.assertFalse(availability())
        ctx['dll'] = catalog['membersDll']
        self.assertTrue(availability())
        ctx['bundle'] = 'old'
        self.assertFalse(availability())
        ctx['bundle'] = catalog['customerMembersBundle']
        self.assertFalse(availability())
        ctx['dll'] = catalog['customerMembersDll']
        self.assertTrue(availability())
        rendered = guide.render(catalog, ctx)
        data = json.loads(rendered.split('const guide=', 1)[1].split(';', 1)[0])
        self.assertTrue(data['cases']['QA-13']['available'])
        ctx['bundle'] = catalog['membersBundle']
        self.assertFalse(availability())

    def test_grants_and_memberships_require_exact_build_pairs(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        pair = {'bundle': 'grants-frontend', 'dll': 'grants-server'}
        catalog['grantBuilds'] = [pair]
        catalog['groupsBuilds'] = [pair]
        catalog['membersBuilds'].append(pair)
        catalog['customerMembersBuilds'] = [
            {'bundle': catalog['customerMembersBundle'], 'dll': catalog['customerMembersDll']}, pair]
        catalog['cases'].append({'id': 'QA-GRANT-TEST', 'feature': 'grantsGui',
                                 'module': 'test', 'title': 'test', 'steps': ['test'], 'expected': 'test'})
        ctx = {'configured': True, 'origin': '', 'bundle': pair['bundle'], 'dll': pair['dll'], 'roles': True}
        def available():
            rendered = guide.render(catalog, ctx)
            return json.loads(rendered.split('const guide=', 1)[1].split(';', 1)[0])['cases']
        cases = available()
        self.assertTrue(all(cases[key]['available'] for key in ('QA-08', 'QA-12', 'QA-13', 'QA-GRANT-TEST')))
        ctx['dll'] = catalog['customerMembersDll']
        self.assertFalse(available()['QA-08']['available'])
        self.assertFalse(available()['QA-GRANT-TEST']['available'])
        ctx['bundle'] = catalog['customerMembersBundle']
        self.assertTrue(available()['QA-13']['available'])
        self.assertFalse(available()['QA-GRANT-TEST']['available'])
        ctx['dll'] = pair['dll']
        self.assertFalse(available()['QA-13']['available'])

    def test_user_state_requires_exact_pair_and_preserves_prior_cases(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        pair = {'bundle': 'state-frontend', 'dll': 'state-server'}
        catalog['userStateBuilds'] = [pair]
        for key in ('groupsBuilds', 'membersBuilds', 'customerMembersBuilds', 'grantBuilds'):
            catalog.setdefault(key, []).append(pair)
        catalog['cases'].append({'id': 'QA-STATE-TEST', 'feature': 'userStateGui',
                                 'module': 'test', 'title': 'test', 'steps': ['test'], 'expected': 'test'})
        ctx = {'configured': True, 'origin': '', 'bundle': pair['bundle'], 'dll': pair['dll'], 'roles': True}
        def available():
            rendered = guide.render(catalog, ctx)
            return json.loads(rendered.split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertTrue(all(available()[key]['available'] for key in ('QA-08', 'QA-12', 'QA-13', 'QA-14', 'QA-STATE-TEST')))
        ctx['dll'] = catalog['grantBuilds'][0]['dll']
        self.assertFalse(available()['QA-STATE-TEST']['available'])
        ctx['bundle'] = catalog['grantBuilds'][0]['bundle']
        self.assertTrue(available()['QA-14']['available'])
        self.assertFalse(available()['QA-STATE-TEST']['available'])
        ctx.update(bundle=pair['bundle'], dll=pair['dll'], configured=False)
        self.assertFalse(available()['QA-STATE-TEST']['available'])

    def test_reviewed_password_pair_keeps_prior_modules_available(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        pair = catalog['userPasswordBuilds'][-1]
        ctx = {'configured': True, 'origin': '', 'bundle': pair['bundle'], 'dll': pair['dll'], 'roles': True, 'profile': 'rc9', 'restored': True}
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        for case in ['QA-08', 'QA-12', 'QA-13', 'QA-14', 'QA-15', 'QA-16']:
            self.assertTrue(cases()[case]['available'], case)
        ctx['dll'] = 'other-server'
        self.assertFalse(cases()['QA-16']['available'])
        ctx['dll'] = pair['dll']
        ctx['bundle'] = 'other-frontend'
        self.assertFalse(cases()['QA-16']['available'])

    def test_password_requires_exact_pair_and_keeps_existing_cases(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        pair = {'bundle': 'password-frontend', 'dll': 'password-server'}
        catalog['userPasswordBuilds'] = [pair]
        ctx = {'configured': True, 'origin': '', 'bundle': pair['bundle'], 'dll': 'old', 'roles': True}
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertFalse(cases()['QA-16']['available'])
        ctx['dll'] = pair['dll']
        self.assertTrue(cases()['QA-16']['available'])
        self.assertEqual(set(cases()), {c['id'] for c in catalog['cases']})
        ctx['bundle'] = 'old'
        self.assertFalse(cases()['QA-16']['available'])
        ctx['configured'] = False
        self.assertFalse(cases()['QA-16']['available'])

    def test_restored_context_and_notes_are_separate(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for profile, home in [('manual', 'qa-wascar'), ('rc9', 'qa-rc9')]:
                directory = root / '.local/labs' / ('manual-qa-' + profile)
                directory.mkdir(parents=True)
                pointer = root / '.local' / home / 'current.json'
                pointer.parent.mkdir(parents=True)
                pointer.write_text(json.dumps({'directory': str(directory)}))
                (directory / 'manual-qa.json').write_text(json.dumps({'profile': profile, 'host':'127.0.0.1', 'directory':str(directory.resolve()), 'webPort': 12345, 'bundleSha256': catalog['groupsBundle']}))
                (directory / 'RESTORE-ESTADO.json').write_text('{"restored":true}')
            original, restored = guide.context(root), guide.context(root, 'rc9')
            self.assertFalse(original['restored'])
            self.assertTrue(restored['restored'])
            rendered = guide.render(catalog, restored)
            data = json.loads(rendered.split('const guide=', 1)[1].split(';', 1)[0])
            self.assertTrue(data['cases']['QA-11']['available'])
            self.assertEqual(data['profile'], 'rc9')
            self.assertIn("profile:guide.profile", rendered)
            self.assertIn("(data.profile||'manual')!==guide.profile", rendered)
            (root / '.local/labs/manual-qa-rc9/manual-qa.json').write_text(json.dumps({'profile':'manual','host':'127.0.0.1','directory':str(directory.resolve()),'webPort':12345}))
            with self.assertRaises(ValueError):
                guide.context(root, 'rc9')

    def test_unavailable_features_are_not_presented_as_available(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        rendered = guide.render(catalog, {'configured': True, 'origin': 'http://127.0.0.1:12345', 'bundle': 'old', 'roles': False})
        self.assertIn('NO DISPONIBLE · pendiente', rendered)
        self.assertIn('"QA-08": {"hash":', rendered)
        data = json.loads(rendered.split('const guide=', 1)[1].split(';', 1)[0])
        self.assertTrue(data['cases']['QA-07']['available'])
        self.assertFalse(data['cases']['QA-08']['available'])
        self.assertFalse(data['cases']['QA-09']['available'])
        self.assertFalse(data['cases']['QA-10']['available'])
        self.assertFalse(data['cases']['QA-12']['available'])
        self.assertFalse(data['cases']['QA-13']['available'])

    def test_user_text_is_escaped_and_duplicate_cases_fail(self):
        case = {'id': 'QA-TEST', 'feature': 'base', 'module': 'test', 'title': '<script>bad</script>', 'steps': ['<img src=x onerror=bad>'], 'expected': 'safe'}
        ctx = {'configured': False, 'origin': '', 'bundle': '', 'roles': False}
        rendered = guide.render({'revision': 'test', 'groupsBundle': 'x', 'cases': [case]}, ctx)
        self.assertIn('&lt;script&gt;bad&lt;/script&gt;', rendered)
        self.assertNotIn('<img src=x', rendered)
        with self.assertRaises(ValueError):
            guide.render({'revision': 'test', 'groupsBundle': 'x', 'cases': [case, case]}, ctx)


    def test_sessions_require_exact_pair_and_preserve_historical_password_modules(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        old = {'bundle': '43f7a19e8ec5aea0e62bfa9d66d4e9031d3ce90207c9af23fab73db48789ce84', 'dll': 'd0a5c95783ecc8e9ae7165be9a1bcd8857ee587b643fac3f07aa6092e6bd4b81'}
        pair = {'bundle': 'sessions-frontend', 'dll': 'sessions-server'}
        catalog['userSessionsBuilds'] = [pair]
        ctx = dict(configured=True, origin='', roles=True, **old)
        def cases():
            return json.loads(guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
        for name in ['QA-08','QA-12','QA-13','QA-14','QA-15','QA-16']:
            self.assertTrue(cases()[name]['available'])
        self.assertFalse(cases()['QA-17']['available'])
        ctx.update(bundle=pair['bundle']); self.assertFalse(cases()['QA-17']['available'])
        ctx.update(dll=pair['dll']); self.assertTrue(cases()['QA-17']['available'])
        ctx.update(bundle=old['bundle']); self.assertFalse(cases()['QA-17']['available'])
        ctx.update(bundle=pair['bundle'], configured=False); self.assertFalse(cases()['QA-17']['available'])

    def test_effective_permissions_require_exact_pair_without_losing_sessions(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        old = {'bundle': 'c9072f1f2847feef2987ac21b4c456eecc466589a4038f2aa5b136a11add5ea3',
               'dll': '5e55ba4628b41b51d84f6ee62043dbf2ed34d84c3bb7959f905833b4c063cf4a'}
        pair = {'bundle': 'effective-frontend', 'dll': 'effective-server'}
        catalog['userEffectivePermissionsBuilds'] = [pair]
        ctx = dict(configured=True, origin='', roles=True, **old)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertFalse(cases()['QA-18']['available'])
        self.assertTrue(cases()['QA-17']['available'])
        ctx['bundle'] = pair['bundle']
        self.assertFalse(cases()['QA-18']['available'])
        ctx['dll'] = pair['dll']
        self.assertTrue(cases()['QA-18']['available'])
        ctx['roles'] = False
        self.assertFalse(cases()['QA-18']['available'])
        ctx['roles'] = True
        ctx['bundle'] = old['bundle']
        self.assertFalse(cases()['QA-18']['available'])
        ctx.update(bundle=pair['bundle'], configured=False)
        self.assertFalse(cases()['QA-18']['available'])

    def test_separate_audit_pair_keeps_modules_but_notifies_only_real_snapshot(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        pair = catalog['auditAdministrativeBuilds'][0]  # Selected50; source52 is not deployed.
        previous = catalog['auditBuilds'][0]
        def cases(ctx):
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        ctx = dict(configured=True, origin='', roles=True, restored=True, **pair)
        for key, case in cases(ctx).items():
            self.assertEqual(case['available'], int(key[3:]) in (set(range(1,10)) | set(range(11,23)) | {24}))
        # A source pair is recognised, without changing either actual QA context.
        real = dict(configured=True, origin='', roles=True, restored=True, **previous)
        self.assertTrue(cases(real)['QA-19']['available'])
        ctx['dll'] = 'unreviewed-server'
        self.assertFalse(cases(ctx)['QA-19']['available'])
        ctx.update(**pair, roles=False)
        self.assertFalse(cases(ctx)['QA-19']['available'])
        ctx.update(roles=True, configured=False)
        self.assertFalse(cases(ctx)['QA-19']['available'])

    def test_audit_requires_exact_pair_and_keeps_available_modules(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        current = catalog['userEffectivePermissionsBuilds'][0]
        pair = catalog['auditBuilds'][0]
        ctx = dict(configured=True, origin='', roles=True, restored=True, **current)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertTrue(cases()['QA-18']['available'])
        self.assertFalse(cases()['QA-19']['available'])
        ctx['bundle'] = pair['bundle']
        self.assertFalse(cases()['QA-19']['available'])
        ctx['dll'] = pair['dll']
        for key, case in cases().items():
            self.assertEqual(case['available'], int(key[3:]) in (set(range(1,10)) | set(range(11,20))))
        ctx['roles'] = False
        self.assertFalse(cases()['QA-19']['available'])
        ctx.update(roles=True, configured=False)
        self.assertFalse(cases()['QA-19']['available'])

    def test_audit_filters_require_exact_pair_without_enabling_old_qa(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        pair = catalog['auditFilterBuilds'][0]
        old = catalog['auditBuilds'][1]
        ctx = dict(configured=True, origin='', roles=True, restored=True, **old)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertTrue(cases()['QA-19']['available'])
        self.assertFalse(cases()['QA-20']['available'])
        ctx.update(bundle=pair['bundle'])
        self.assertFalse(cases()['QA-20']['available'])
        ctx.update(dll=pair['dll'])
        self.assertTrue(cases()['QA-20']['available'])
        for name in ('QA-08','QA-12','QA-13','QA-14','QA-15','QA-16','QA-17','QA-18','QA-19'):
            self.assertTrue(cases()[name]['available'])
        ctx.update(roles=False)
        self.assertFalse(cases()['QA-20']['available'])
        ctx.update(roles=True, configured=False)
        self.assertFalse(cases()['QA-20']['available'])

    def test_audit_detail_requires_future_exact_pair_and_ready_roles(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        pair = catalog['auditDetailBuilds'][0]
        old = catalog['auditFilterBuilds'][0]
        ctx = dict(configured=True, origin='', roles=True, restored=True, **old)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertTrue(cases()['QA-20']['available'])
        self.assertFalse(cases()['QA-21']['available'])
        ctx.update(bundle=pair['bundle'])
        self.assertFalse(cases()['QA-21']['available'])
        ctx.update(dll=pair['dll'])
        self.assertTrue(cases()['QA-21']['available'])
        self.assertTrue(all(cases()[name]['available'] for name in ('QA-12','QA-13','QA-14','QA-15','QA-16','QA-17','QA-18','QA-19','QA-20')))
        ctx.update(bundle=old['bundle'])
        self.assertFalse(cases()['QA-21']['available'])
        ctx.update(bundle=pair['bundle'], roles=False)
        self.assertFalse(cases()['QA-21']['available'])
        ctx.update(roles=True, configured=False)
        self.assertFalse(cases()['QA-21']['available'])

    def test_administrative_audit_requires_exact_pair_roles_and_configuration(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        old, pair = catalog['auditDetailBuilds'][0], catalog['auditAdministrativeBuilds'][0]
        ctx = dict(configured=True, origin='', roles=True, restored=True, **old)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertTrue(cases()['QA-21']['available'])
        self.assertFalse(cases()['QA-22']['available'])
        ctx.update(bundle=pair['bundle'])
        self.assertFalse(cases()['QA-22']['available'])
        ctx.update(dll=pair['dll'])
        self.assertTrue(cases()['QA-22']['available'])
        self.assertTrue(all(cases()[key]['available'] for key in ('QA-08','QA-12','QA-13','QA-14','QA-15','QA-16','QA-17','QA-18','QA-19','QA-20','QA-21')))
        ctx.update(bundle=old['bundle'])
        self.assertFalse(cases()['QA-22']['available'])
        ctx.update(bundle=pair['bundle'], roles=False)
        self.assertFalse(cases()['QA-22']['available'])
        ctx.update(roles=True, configured=False)
        self.assertFalse(cases()['QA-22']['available'])

    def test_navigation_requires_exact_pair_and_ready_roles(self):
        self.check_new_feature_pair('QA-23', 'adminNavigationBuilds', 'QA-24', 'inventoryMovementBuilds')

    def test_inventory_movement_requires_exact_pair_and_ready_roles(self):
        self.check_new_feature_pair('QA-24', 'inventoryMovementBuilds', 'QA-23', 'adminNavigationBuilds')

    def test_selection_and_duplicate_stay_unavailable_without_reviewed_pairs(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        for key in ('adminSelectionBuilds', 'inventoryDuplicateBuilds'):
            catalog.pop(key, None)
        # Synthetic additions do not depend on which candidates are installed locally.
        catalog['cases'] = [dict(id=case_id, module='test', title='test', feature=feature,
                                 steps=['step'], expected='expected') for case_id, feature in
                            [('QA-25', 'adminSelectionGui'), ('QA-26', 'inventoryDuplicateGui')]]
        ctx = dict(configured=True, origin='', roles=True, restored=True,
                   bundle='frontend', dll='server')
        cases = json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertTrue(all(not case['available'] for case in cases.values()))

    def test_selection_and_duplicate_require_exact_independent_pairs(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id=case_id, module='test', title='test', feature=feature,
                                 steps=['step'], expected='expected') for case_id, feature in
                            [('QA-25', 'adminSelectionGui'), ('QA-26', 'inventoryDuplicateGui')]]
        catalog['adminSelectionBuilds'] = [dict(bundle='frontend-a', dll='server-a')]
        catalog['inventoryDuplicateBuilds'] = [dict(bundle='frontend-b', dll='server-b')]
        for target, key, other in [('QA-25', 'adminSelectionBuilds', 'QA-26'),
                                   ('QA-26', 'inventoryDuplicateBuilds', 'QA-25')]:
            pair = catalog[key][0]
            for configured, roles, bundle, dll, allowed in [
                (True, True, pair['bundle'], pair['dll'], True),
                (True, True, pair['bundle'], 'unreviewed-server', False),
                (True, True, 'unreviewed-frontend', pair['dll'], False),
                (True, False, pair['bundle'], pair['dll'], False),
                (False, True, pair['bundle'], pair['dll'], False)]:
                with self.subTest(target=target, configured=configured, roles=roles, bundle=bundle, dll=dll):
                    ctx = dict(configured=configured, origin='', roles=roles, restored=True, bundle=bundle, dll=dll)
                    cases = json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
                    self.assertEqual(cases[target]['available'], allowed)
                    self.assertFalse(cases[other]['available'])

    def test_poe_face_gate_fails_closed_and_requires_exact_pair(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id='QA-27', module='test', title='test', feature='inventoryPoeFaceGui', steps=['step'], expected='expected')]
        catalog.pop('inventoryPoeFaceBuilds', None)
        ctx = dict(configured=True, origin='', roles=True, restored=True, bundle='frontend', dll='server')
        def available():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']['QA-27']['available']
        self.assertFalse(available())
        catalog['inventoryPoeFaceBuilds'] = [dict(bundle='frontend', dll='server')]
        for configured, roles, bundle, dll, expected in [
            (True, True, 'frontend', 'server', True),
            (False, True, 'frontend', 'server', False),
            (True, False, 'frontend', 'server', False),
            (True, True, 'frontend', 'unreviewed-server', False),
            (True, True, 'unreviewed-frontend', 'server', False),
            (True, True, '', '', False)]:
            with self.subTest(configured=configured, roles=roles, bundle=bundle, dll=dll):
                ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                self.assertEqual(available(), expected)

    def test_55_59_new_gates_are_independent_and_fail_closed(self):
        features = [('QA-28', 'auditContextGui', 'auditContextBuilds'),
                    ('QA-29', 'inventoryBatchGui', 'inventoryBatchBuilds'),
                    ('QA-30', 'inventoryPatchGui', 'inventoryPatchBuilds'),
                    ('QA-31', 'inventoryHierarchyGui', 'inventoryHierarchyBuilds')]
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id=case_id, module='test', title='test', feature=feature,
                                 steps=['step'], expected='expected')
                            for case_id, feature, key in features]
        for _, _, key in features:
            catalog.pop(key, None)
        ctx = dict(configured=True, origin='', roles=True, restored=True,
                   bundle='frontend', dll='server')
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertTrue(all(not case['available'] for case in cases().values()))
        for target, _, key in features:
            catalog[key] = [dict(bundle='frontend', dll='server')]
            for configured, roles, bundle, dll, expected in [
                (True, True, 'frontend', 'server', True),
                (False, True, 'frontend', 'server', False),
                (True, False, 'frontend', 'server', False),
                (True, True, 'other-frontend', 'server', False),
                (True, True, 'frontend', 'other-server', False)]:
                with self.subTest(target=target, configured=configured, roles=roles, bundle=bundle, dll=dll):
                    ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                    result = cases()
                    self.assertEqual(result[target]['available'], expected)
                    self.assertTrue(all(not case['available'] for key_id, case in result.items() if key_id != target))
            catalog.pop(key)

    def test_client_changes_requires_its_own_reviewed_pair_and_ready_roles(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id='QA-10', module='test', title='test', feature='clientChangesGui',
                                 steps=['step'], expected='expected')]
        catalog.pop('clientChangesBuilds', None)
        pair = dict(bundle='notice-frontend', dll='notice-server')
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        def available():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']['QA-10']['available']
        self.assertFalse(available())
        # Other reviewed modules cannot implicitly enable collaboration.
        catalog['inventoryBatchBuilds'] = [pair]
        self.assertFalse(available())
        catalog['clientChangesBuilds'] = [pair]
        for configured, roles, bundle, dll, expected in [
            (True, True, pair['bundle'], pair['dll'], True),
            (False, True, pair['bundle'], pair['dll'], False),
            (True, False, pair['bundle'], pair['dll'], False),
            (True, True, 'old-frontend', pair['dll'], False),
            (True, True, pair['bundle'], 'old-server', False),
            (True, True, '', '', False)]:
            with self.subTest(configured=configured, roles=roles, bundle=bundle, dll=dll):
                ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                self.assertEqual(available(), expected)

    def test_device_batch_delete_requires_its_own_reviewed_pair_and_ready_roles(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id='QA-32', module='test', title='test', feature='inventoryDeleteBatchGui',
                                 steps=['step'], expected='expected')]
        catalog.pop('inventoryDeleteBatchBuilds', None)
        pair = dict(bundle='delete-frontend', dll='delete-server')
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        def available():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']['QA-32']['available']
        self.assertFalse(available())
        # Other reviewed modules cannot implicitly enable deletion.
        catalog['inventoryBatchBuilds'] = [pair]
        self.assertFalse(available())
        catalog['inventoryDeleteBatchBuilds'] = [pair]
        for configured, roles, bundle, dll, expected in [
            (True, True, pair['bundle'], pair['dll'], True),
            (False, True, pair['bundle'], pair['dll'], False),
            (True, False, pair['bundle'], pair['dll'], False),
            (True, True, 'old-frontend', pair['dll'], False),
            (True, True, pair['bundle'], 'old-server', False),
            (True, True, '', '', False)]:
            with self.subTest(configured=configured, roles=roles, bundle=bundle, dll=dll):
                ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                self.assertEqual(available(), expected)

    def test_room_device_move_requires_its_own_reviewed_pair_and_ready_roles(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id='QA-33', module='test', title='test', feature='roomDeviceMoveGui',
                                 steps=['step'], expected='expected')]
        catalog.pop('roomDeviceMoveBuilds', None)
        pair = dict(bundle='room-frontend', dll='room-server')
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        def available():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']['QA-33']['available']
        self.assertFalse(available())
        # Other reviewed modules cannot implicitly enable room movement.
        catalog['inventoryBatchBuilds'] = [pair]
        self.assertFalse(available())
        catalog['roomDeviceMoveBuilds'] = [pair]
        for configured, roles, bundle, dll, expected in [
            (True, True, pair['bundle'], pair['dll'], True),
            (False, True, pair['bundle'], pair['dll'], False),
            (True, False, pair['bundle'], pair['dll'], False),
            (True, True, 'old-frontend', pair['dll'], False),
            (True, True, pair['bundle'], 'old-server', False),
            (True, True, '', '', False)]:
            with self.subTest(configured=configured, roles=roles, bundle=bundle, dll=dll):
                ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                self.assertEqual(available(), expected)

    def test_63_68_gates_are_independent_and_fail_closed(self):
        features = [('QA-34', 'adminGroupRelationsGui', 'adminGroupRelationsBuilds'),
                    ('QA-35', 'poeBudgetGui', 'poeBudgetBuilds'),
                    ('QA-36', 'inventoryCompensationGui', 'inventoryCompensationBuilds')]
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id=case_id, module='test', title='test', feature=feature,
                                 steps=['step'], expected='expected') for case_id, feature, _ in features]
        for _, _, key in features:
            catalog.pop(key, None)
        ctx = dict(configured=True, origin='', roles=True, restored=True, bundle='front68', dll='server68')
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertTrue(all(not case['available'] for case in cases().values()))
        for target, _, key in features:
            catalog[key] = [dict(bundle='front68', dll='server68')]
            for configured, roles, bundle, dll, expected in [
                (True, True, 'front68', 'server68', True),
                (False, True, 'front68', 'server68', False),
                (True, False, 'front68', 'server68', False),
                (True, True, 'other-front', 'server68', False),
                (True, True, 'front68', 'other-server', False)]:
                with self.subTest(target=target, configured=configured, roles=roles, bundle=bundle, dll=dll):
                    ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                    actual = cases()
                    self.assertEqual(actual[target]['available'], expected)
                    self.assertTrue(all(not value['available'] for case_id, value in actual.items() if case_id != target))
            catalog.pop(key)

    def test_69_83_consultation_and_cancel_gates_require_independent_exact_pairs(self):
        features = [('QA-36', 'inventoryCompensationCancelGui', 'inventoryCompensationCancelBuilds'),
                    ('QA-37', 'inventorySearchGui', 'inventorySearchBuilds'),
                    ('QA-38', 'inventoryPortViewGui', 'inventoryPortViewBuilds'),
                    ('QA-39', 'inventoryConnectionViewGui', 'inventoryConnectionViewBuilds')]
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id=case_id, module='test', title='test', feature=feature,
                                 steps=['step'], expected='expected') for case_id, feature, _ in features]
        for _, _, key in features:
            catalog.pop(key, None)
        pair = dict(bundle='reviewed83-front', dll='reviewed83-server')
        catalog['inventoryCompensationBuilds'] = [pair]
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        # Earlier undo builds cannot enable the newly specified cancel/reopen behavior.
        self.assertTrue(all(not value['available'] for value in cases().values()))
        for target, _, key in features:
            catalog[key] = [pair]
            for configured, roles, bundle, dll, expected in [
                (True, True, pair['bundle'], pair['dll'], True),
                (False, True, pair['bundle'], pair['dll'], False),
                (True, False, pair['bundle'], pair['dll'], False),
                (True, True, 'old-front', pair['dll'], False),
                (True, True, pair['bundle'], 'old-server', False)]:
                with self.subTest(target=target, configured=configured, roles=roles, bundle=bundle, dll=dll):
                    ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                    result = cases()
                    self.assertEqual(result[target]['available'], expected)
                    self.assertTrue(all(not value['available'] for case_id, value in result.items() if case_id != target))
            catalog.pop(key)

    def test_84_98_csv_gates_require_independent_exact_pairs(self):
        features = [('QA-40', 'inventoryPortsCsvGui', 'reportsPortsBuilds'),
                    ('QA-41', 'inventoryConnectionsCsvGui', 'reportsConnectionsBuilds'),
                    ('QA-42', 'inventoryRackCsvGui', 'reportsRackBuilds')]
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id=case_id, module='test', title='test', feature=feature,
                                 steps=['step'], expected='expected') for case_id, feature, _ in features]
        for _, _, key in features:
            catalog.pop(key, None)
        pair = dict(bundle='reviewed98-front', dll='reviewed98-server')
        catalog['inventoryPortViewBuilds'] = [pair]
        catalog['inventoryConnectionViewBuilds'] = [pair]
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        # Consultation read access does not enable CSV generation without its own reviewed pair.
        self.assertTrue(all(not value['available'] for value in cases().values()))
        for target, _, key in features:
            catalog[key] = [pair]
            for configured, roles, bundle, dll, expected in [
                (True, True, pair['bundle'], pair['dll'], True),
                (False, True, pair['bundle'], pair['dll'], False),
                (True, False, pair['bundle'], pair['dll'], False),
                (True, True, 'old-front', pair['dll'], False),
                (True, True, pair['bundle'], 'old-server', False)]:
                with self.subTest(target=target, configured=configured, roles=roles, bundle=bundle, dll=dll):
                    ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                    result = cases()
                    self.assertEqual(result[target]['available'], expected)
                    self.assertTrue(all(not value['available'] for case_id, value in result.items() if case_id != target))
            catalog.pop(key)

    def test_99_113_printable_gates_require_independent_exact_pairs(self):
        features = [('QA-43', 'printableRackGui', 'printableRackBuilds'),
                    ('QA-44', 'printableClientGui', 'printableClientBuilds'),
                    ('QA-45', 'printableRackLabelsGui', 'printableRackLabelBuilds')]
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id=case_id, module='test', title='test', feature=feature,
                                 steps=['step'], expected='expected') for case_id, feature, _ in features]
        for _, _, key in features:
            catalog.pop(key, None)
        pair = dict(bundle='reviewed113-front', dll='reviewed113-server')
        catalog['reportsPortsBuilds'] = [pair]
        catalog['reportsConnectionsBuilds'] = [pair]
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        # CSV compatibility cannot enable printable HTML without its own reviewed pair.
        self.assertTrue(all(not value['available'] for value in cases().values()))
        for target, _, key in features:
            catalog[key] = [pair]
            for configured, roles, bundle, dll, expected in [
                (True, True, pair['bundle'], pair['dll'], True),
                (False, True, pair['bundle'], pair['dll'], False),
                (True, False, pair['bundle'], pair['dll'], False),
                (True, True, 'old-front', pair['dll'], False),
                (True, True, pair['bundle'], 'old-server', False)]:
                with self.subTest(target=target, configured=configured, roles=roles, bundle=bundle, dll=dll):
                    ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                    result = cases()
                    self.assertEqual(result[target]['available'], expected)
                    self.assertTrue(all(not value['available'] for case_id, value in result.items() if case_id != target))
            catalog.pop(key)

    def test_114_128_catalog_gates_require_independent_exact_pairs(self):
        features = [('QA-46', 'inventoryCatalogGui', 'inventoryCatalogBuilds'),
                    ('QA-47', 'inventoryCatalogCreateGui', 'inventoryCatalogCreateBuilds'),
                    ('QA-48', 'inventoryCatalogSafetyGui', 'inventoryCatalogSafetyBuilds')]
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id=case_id, module='test', title='test', feature=feature,
                                 steps=['step'], expected='expected') for case_id, feature, _ in features]
        for _, _, key in features:
            catalog.pop(key, None)
        pair = dict(bundle='reviewed128-front', dll='reviewed128-server')
        catalog['printableRackBuilds'] = [pair]
        catalog['printableClientBuilds'] = [pair]
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        # Printable compatibility cannot enable catalog creation without its own reviewed pair.
        self.assertTrue(all(not value['available'] for value in cases().values()))
        for target, _, key in features:
            catalog[key] = [pair]
            for configured, roles, bundle, dll, expected in [
                (True, True, pair['bundle'], pair['dll'], True),
                (False, True, pair['bundle'], pair['dll'], False),
                (True, False, pair['bundle'], pair['dll'], False),
                (True, True, 'old-front', pair['dll'], False),
                (True, True, pair['bundle'], 'old-server', False)]:
                with self.subTest(target=target, configured=configured, roles=roles, bundle=bundle, dll=dll):
                    ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                    result = cases()
                    self.assertEqual(result[target]['available'], expected)
                    self.assertTrue(all(not value['available'] for case_id, value in result.items() if case_id != target))
            catalog.pop(key)

    def test_129_143_favorites_gates_require_independent_exact_pairs(self):
        features = [('QA-49', 'catalogFavoritesGui', 'catalogFavoritesBuilds'),
                    ('QA-50', 'catalogFavoritesPersistenceGui', 'catalogFavoritesPersistenceBuilds'),
                    ('QA-51', 'catalogFavoritesSafetyGui', 'catalogFavoritesSafetyBuilds')]
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id=case_id, module='test', title='test', feature=feature,
                                 steps=['step'], expected='expected') for case_id, feature, _ in features]
        for _, _, key in features:
            catalog.pop(key, None)
        pair = dict(bundle='reviewed143-front', dll='reviewed143-server')
        catalog['printableRackBuilds'] = [pair]
        catalog['printableClientBuilds'] = [pair]
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        # Printable compatibility cannot enable catalog creation without its own reviewed pair.
        self.assertTrue(all(not value['available'] for value in cases().values()))
        for target, _, key in features:
            catalog[key] = [pair]
            for configured, roles, bundle, dll, expected in [
                (True, True, pair['bundle'], pair['dll'], True),
                (False, True, pair['bundle'], pair['dll'], False),
                (True, False, pair['bundle'], pair['dll'], False),
                (True, True, 'old-front', pair['dll'], False),
                (True, True, pair['bundle'], 'old-server', False)]:
                with self.subTest(target=target, configured=configured, roles=roles, bundle=bundle, dll=dll):
                    ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                    result = cases()
                    self.assertEqual(result[target]['available'], expected)
                    self.assertTrue(all(not value['available'] for case_id, value in result.items() if case_id != target))
            catalog.pop(key)

    def test_144_158_rack_svg_gates_require_independent_exact_pairs(self):
        features = [('QA-52', 'rackSvgGui', 'rackSvgBuilds'),
                    ('QA-53', 'rackSvgFacesGui', 'rackSvgFacesBuilds'),
                    ('QA-54', 'rackSvgSafetyGui', 'rackSvgSafetyBuilds')]
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id=case_id, module='test', title='test', feature=feature,
                                 steps=['step'], expected='expected') for case_id, feature, _ in features]
        for _, _, key in features:
            catalog.pop(key, None)
        pair = dict(bundle='reviewed158-front', dll='reviewed158-server')
        catalog['printableRackBuilds'] = [pair]
        catalog['printableClientBuilds'] = [pair]
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        # Printable compatibility cannot enable catalog creation without its own reviewed pair.
        self.assertTrue(all(not value['available'] for value in cases().values()))
        for target, _, key in features:
            catalog[key] = [pair]
            for configured, roles, bundle, dll, expected in [
                (True, True, pair['bundle'], pair['dll'], True),
                (False, True, pair['bundle'], pair['dll'], False),
                (True, False, pair['bundle'], pair['dll'], False),
                (True, True, 'old-front', pair['dll'], False),
                (True, True, pair['bundle'], 'old-server', False)]:
                with self.subTest(target=target, configured=configured, roles=roles, bundle=bundle, dll=dll):
                    ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                    result = cases()
                    self.assertEqual(result[target]['available'], expected)
                    self.assertTrue(all(not value['available'] for case_id, value in result.items() if case_id != target))
            catalog.pop(key)

    def test_159_173_private_templates_gates_require_independent_exact_pairs(self):
        features = [('QA-55', 'privateTemplatesGui', 'privateTemplatesBuilds'),
                    ('QA-56', 'privateTemplatesCreateGui', 'privateTemplatesCreateBuilds'),
                    ('QA-57', 'privateTemplatesSafetyGui', 'privateTemplatesSafetyBuilds')]
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog['cases'] = [dict(id=case_id, module='test', title='test', feature=feature,
                                 steps=['step'], expected='expected') for case_id, feature, _ in features]
        for _, _, key in features:
            catalog.pop(key, None)
        pair = dict(bundle='reviewed173-front', dll='reviewed173-server')
        catalog['printableRackBuilds'] = [pair]
        catalog['printableClientBuilds'] = [pair]
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        # Printable compatibility cannot enable private templates without their own reviewed pair.
        self.assertTrue(all(not value['available'] for value in cases().values()))
        for target, _, key in features:
            catalog[key] = [pair]
            for configured, roles, bundle, dll, expected in [
                (True, True, pair['bundle'], pair['dll'], True),
                (False, True, pair['bundle'], pair['dll'], False),
                (True, False, pair['bundle'], pair['dll'], False),
                (True, True, 'old-front', pair['dll'], False),
                (True, True, pair['bundle'], 'old-server', False)]:
                with self.subTest(target=target, configured=configured, roles=roles, bundle=bundle, dll=dll):
                    ctx.update(configured=configured, roles=roles, bundle=bundle, dll=dll)
                    result = cases()
                    self.assertEqual(result[target]['available'], expected)
                    self.assertTrue(all(not value['available'] for case_id, value in result.items() if case_id != target))
            catalog.pop(key)

    def test_174_179_private_rename_requires_its_own_exact_pair(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        pair = dict(bundle='rename-frontend', dll='rename-server')
        catalog.pop('privateTemplateRenameBuilds', None)
        catalog['privateTemplatesBuilds'] = [pair]
        ctx = dict(configured=True, origin='', roles=True, restored=True, **pair)
        result = json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertFalse(result['QA-58']['available'])
        self.check_new_feature_pair('QA-58', 'privateTemplateRenameBuilds', 'QA-55', 'privateTemplatesBuilds')

    def test_180_185_power_compensation_requires_its_own_exact_pair(self):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        catalog.pop('compensationPowerBuilds', None)
        pair = dict(bundle='new-power-frontend', dll='new-power-server')
        catalog['inventoryCompensationBuilds'] = [pair]
        catalog['inventoryCompensationCancelBuilds'] = [pair]
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        result = json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertFalse(result['QA-59']['available'])
        self.check_new_feature_pair('QA-59', 'compensationPowerBuilds', 'QA-36', 'inventoryCompensationCancelBuilds')

    def test_368_397_spreadsheet_requires_own_exact_pair_and_ready_roles(self):
        for case in ['QA-60', 'QA-61', 'QA-62']:
            with self.subTest(case=case):
                self.check_new_feature_pair(case, 'inventorySpreadsheetBuilds', 'QA-59', 'compensationPowerBuilds')

    def check_new_feature_pair(self, case_id, builds_key, other_case, other_builds):
        catalog = json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        pair = dict(bundle='reviewed-frontend', dll='reviewed-server')
        catalog[builds_key] = [pair]
        catalog[other_builds] = [dict(bundle='another-frontend', dll='another-server')]
        ctx = dict(configured=True, origin='', roles=True, restored=True, bundle='old-frontend', dll='old-server')
        def cases():
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
        self.assertFalse(cases()[case_id]['available'])
        ctx['bundle'] = pair['bundle']
        self.assertFalse(cases()[case_id]['available'])
        ctx['dll'] = pair['dll']
        self.assertTrue(cases()[case_id]['available'])
        self.assertFalse(cases()[other_case]['available'])
        ctx['bundle'] = 'old-frontend'
        self.assertFalse(cases()[case_id]['available'])
        ctx.update(**pair, roles=False)
        self.assertFalse(cases()[case_id]['available'])
        ctx.update(roles=True, configured=False)
        self.assertFalse(cases()[case_id]['available'])

if __name__ == '__main__':
    unittest.main()
