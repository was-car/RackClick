"""Adversarial authoring checks; no database, VM or private reference required."""
import copy
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('batch50_authoring_tests',ROOT/'tools/build_hardware_batch50.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def fixture():
    return b.c.load((ROOT/b.SOURCES[0]).read_bytes())['models'][0]

class Batch50AuthoringTests(unittest.TestCase):
    def test_valid_actual_authoring(self):
        row=fixture();self.assertIs(b.validate_model(row),row)

    def test_invalid_geometry_mapping_and_types(self):
        mutations=[
            lambda x:x['definition']['provenance'].update(source=17),
            lambda x:x['visual']['faces']['front']['decorations'].append(17),
            lambda x:x['evidence']['sources'].append(17),
            lambda x:x['evidence']['sources'][0].update(url=17),
            lambda x:x['evidence']['sources'][0].update(sha256=17),
            lambda x:x['evidence']['referenceAssets'].append(17),
            lambda x:x['evidence']['referenceAssets'][0].update(sha256=17),
            lambda x:x['definition']['groups'][0].update(powerRole='inlet'),
            lambda x:x['definition']['groups'][0].update(type='usb'),
            lambda x:x['definition'].update(rackUnits=1),
            lambda x:x['definition']['dimensionsMm'].update(height=float('nan')),
            lambda x:x['definition']['dimensionsMm'].update(height=True),
            lambda x:x['visual']['faces']['rear']['banks'][0].update(dx=0),
            lambda x:x['visual']['faces']['rear']['banks'][0].update(x=-1),
            lambda x:x['visual']['faces']['rear']['banks'][0].update(x=10000),
            lambda x:x['visual']['faces']['rear']['banks'][0]['rows'][0].append(1),
            lambda x:x['visual']['faces']['rear']['banks'][0].update(groupKey='other'),
            lambda x:x['visual']['faces']['front']['decorations'].append(dict(kind='image',href='https://example.test/a.svg')),
            lambda x:x['visual']['faces']['front']['plate'].update(fill='url(javascript:evil)'),
            lambda x:x['visual']['faces']['front']['decorations'].append(dict(kind='text',x=1,y=1,text='\x00',size=10,fill='#fff')),
        ]
        for index,mutate in enumerate(mutations):
            with self.subTest(index=index):
                model=copy.deepcopy(fixture());mutate(model)
                with self.assertRaises(b.c.CatalogError):b.validate_model(model)

    def test_all_current_rows_have_exact_mapping(self):
        for source in b.SOURCES:
            path=ROOT/source
            if path.is_file():
                for model in b.c.load(path.read_bytes())['models']:
                    with self.subTest(model=model['definition']['key']):b.validate_model(model)

    def test_escaped_text_is_data_not_svg_markup(self):
        row=copy.deepcopy(fixture());row['visual']['faces']['front']['decorations'].append(dict(kind='text',x=10,y=20,text='<svg onload=alert(1)> Ω',size=10,fill='#fff'))
        b.validate_model(row)

if __name__=='__main__':unittest.main()
