"""Availability must follow the exact RC9 Excel pair, never older XLSX/QA712."""
import hashlib,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('qa_guide',ROOT/'tools/windows/qa_guide.py');guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
class ExcelGuide832(unittest.TestCase):
    def test_exact_pair_and_roles_are_required_for_each_new_case(self):
        original=json.loads(guide.CATALOG.read_bytes())
        for case_id,key in [('QA-75','rc9ExcelBuilds'),('QA-76','rc9ExcelTextBuilds'),('QA-77','rc9ExcelSafetyBuilds')]:
            with self.subTest(case=case_id):
                catalog=json.loads(json.dumps(original));pair=dict(bundle='rc9-excel-frontend',dll='rc9-excel-server');catalog[key]=[pair]
                ctx=dict(configured=True,origin='',roles=True,restored=True,bundle='old',dll='old')
                def cases():return json.loads(guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
                self.assertFalse(cases()[case_id]['available']);ctx['bundle']=pair['bundle'];self.assertFalse(cases()[case_id]['available'])
                ctx['dll']=pair['dll'];self.assertTrue(cases()[case_id]['available']);self.assertFalse(cases()['QA-60']['available'])
                ctx['bundle']='old';self.assertFalse(cases()[case_id]['available']);ctx.update(**pair,roles=False);self.assertFalse(cases()[case_id]['available'])
                ctx.update(roles=True,configured=False);self.assertFalse(cases()[case_id]['available'])
    def test_prior74_except_three_availability_intros_and_private_results_unchanged(self):
        catalog=json.loads(guide.CATALOG.read_bytes());self.assertGreaterEqual(len(catalog['cases']),77)
        start=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-773-832/QA-ANTERIOR.json').read_bytes())
        baseline=json.loads(json.dumps(catalog['cases'][:74]))
        old='NO DISPONIBLE en QA185 actual. Espera a que esta guía marque DISPONIBLE con el servidor y GUI nuevos; no marques Pass sobre la versión anterior. Tus resultados anteriores se conservan.'
        current='Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Ejecuta INICIAR-QA-RESTAURADO.cmd y usa su guía y ACCESO-PRIVADO.txt; elige Español y pulsa Ctrl+F5. Usa cuentas ficticias y otro perfil respecto a QA original. Si no está disponible, marca Bloqueado. Tus resultados y observaciones anteriores se conservan.'
        for case in baseline:
            if case['id'] in ['QA-60','QA-61','QA-62']:
                self.assertIn(case['steps'][0],[old,current]);case['steps'][0]=old
        self.assertEqual(hashlib.sha256(json.dumps(baseline,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),start['first74CasesSha256'])
        self.assertEqual([c['id'] for c in catalog['cases'][74:77]],['QA-75','QA-76','QA-77'])
if __name__=='__main__':unittest.main()
