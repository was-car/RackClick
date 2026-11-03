"""Focused seven-media authoring tests; no database/build or published fixtures changed."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).absolute().parents[2]
spec = importlib.util.spec_from_file_location('physical_v3_unit', ROOT/'tools/hardware_physical_v3.py')
v3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v3)


class PhysicalV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads((ROOT/'development/hardware/selected506g/core.json').read_bytes())['models'][0]
        cls.revision = cls.reference['definition']['revision']

    def row(self, kind='sfp56'):
        row = copy.deepcopy(self.reference)
        row['definition']['groups'][0]['type'] = kind
        return row

    def test_seven_types_and_original_object_without_mutation(self):
        self.assertEqual(set(v3.ALLOWED_TYPES), {'rj45','sfp','sfp28','sfp56','qsfp','qsfpdd','power'})
        for row in (copy.deepcopy(self.reference),self.row(),self.row('qsfpdd')):
            before = copy.deepcopy(row)
            self.assertIs(v3.validate_model(row,self.revision),row)
            self.assertEqual(row,before)

    def test_unknown_aliases_and_other_media_are_not_mapped(self):
        for kind in ('qsfp-dd','qsfp_dd','sfp56-dd','qsfp56','osfp','rj45_poe','usb_a'):
            row = self.row(kind);before = copy.deepcopy(row)
            with self.assertRaisesRegex(v3.CatalogError,'physical_v3_connector_unsupported'):
                v3.validate_model(row,self.revision)
            self.assertEqual(row,before)

    def test_historical_v2_still_rejects_both_new_types(self):
        for kind in ('sfp56','qsfpdd'):
            with self.assertRaises(v3.CatalogError):v3.engine.validate_model(self.row(kind),self.revision)

    def test_runtime_group_limit_96_and_97_no_truncation(self):
        row = self.row();group = row['definition']['groups'][0]
        row['definition']['groups'] = [group]
        for count,valid in ((96,True),(97,False)):
            group['count'] = count;group['face'] = 'front'
            row['visual']['faces']['front'].update(width=2000,banks=[dict(groupKey=group['key'],rows=[list(range(1,count+1))],x=20,y=40,dx=10,dy=0,w=8,h=20)])
            row['visual']['faces']['rear']['banks'] = []
            before = copy.deepcopy(row)
            if valid:self.assertIs(v3.validate_model(row,self.revision),row)
            else:
                with self.assertRaisesRegex(v3.CatalogError,'runtime_group_limit'):v3.validate_model(row,self.revision)
            self.assertEqual(row,before)

    def test_bank_identity_and_geometry_stay_validated(self):
        reference = self.row('qsfpdd');face = next(v for v in reference['visual']['faces'].values() if v['banks'])
        for field,value in (('groupKey','missing'),('x',-1),('rows',[[1,1]])):
            row = copy.deepcopy(reference);target = next(v for v in row['visual']['faces'].values() if v['banks'])
            target['banks'][0][field] = value;before = copy.deepcopy(row)
            with self.assertRaises(v3.CatalogError):v3.validate_model(row,self.revision)
            self.assertEqual(row,before)

    def test_name_prefix_raw_100_scalar_boundary_and_unicode(self):
        for field in ('name','prefix'):
            for value in ('A'*100,'\U0001f600'*100,'e\u0301'*50):
                row=self.row();row['definition']['groups'][0][field]=value;before=copy.deepcopy(row)
                self.assertIs(v3.validate_model(row,self.revision),row);self.assertEqual(row,before)
            for value in ('A'*101,'\U0001f600'*101,'A\x85B','\ud800'):
                row=self.row();row['definition']['groups'][0][field]=value
                with self.assertRaises(v3.CatalogError):v3.validate_model(row,self.revision)

    def test_real_types_are_retained_in_memory_csharp_sql_and_json(self):
        for kind in ('sfp56','qsfpdd'):
            model=v3.validate_model(self.row(kind),self.revision)['definition']
            pins=[dict(key=model['key'],revision=model['revision'],sha256=v3.c.sha(v3.c.canonical(model)))]
            self.assertIn(('"'+kind+'"').encode(),v3.base.server_source([model]))
            self.assertIn(("E'"+kind+"'").encode(),v3.g.sql_source([model],pins))
            projection=v3.c.projection(dict(definitions=[model]))
            self.assertEqual(projection['profiles'][0]['groups'][0]['type'],kind)

    def test_revision_validation_has_no_shared_global_leak(self):
        for revision in ('fixture-v3-a','fixture-v3-b','fixture-v3-a'):
            row=self.row();row['definition']['revision']=revision
            self.assertIs(v3.validate_model(row,revision),row)
            with self.assertRaises(v3.CatalogError):v3.validate_model(row,'other-revision')


if __name__=='__main__':unittest.main()
