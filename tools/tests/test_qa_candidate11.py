"""QA attribution guards; synthetic records never become Wascar's results."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import qa_candidate11 as qa

class Candidate11Qa(unittest.TestCase):
    def setUp(self):
        self.spec=qa.spec()
        self.report={'format':'RackClick-QA-Candidate-v1','candidate':copy.deepcopy(qa.CANDIDATE),
          'environment':{'origin':'https://192.0.2.11:5443','candidateConfirmed':True},'records':{}}
        for case in self.spec['cases']:
            self.report['records'][case['id']]={'result':'Pass','notes':'Synthetic fixture, not a user result',
              'caseSha256':case['caseSha256'],'updatedUtc':'2026-11-02T09:00:00Z'}

    def test_all_pass_never_adopts_or_unblocks_production(self):
        r=qa.assess(self.report,self.spec)
        self.assertTrue(r['manualChecklistComplete']);self.assertFalse(r['adoption']);self.assertFalse(r['productionReady'])
        self.assertGreater(len(r['pending']),0)

    def test_prior_installer_and_old_qa_format_are_rejected(self):
        for field,value in [('edition','10'),('schema',15),('archiveSha256','0'*64)]:
            data=copy.deepcopy(self.report);data['candidate'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):qa.assess(data,self.spec)
        data=copy.deepcopy(self.report);data['format']='RackClick-QA-v1'
        with self.assertRaises(ValueError):qa.assess(data,self.spec)

    def test_missing_case_and_stale_hash_prevent_completion(self):
        key=next(iter(self.report['records']));del self.report['records'][key]
        self.assertFalse(qa.assess(self.report,self.spec)['manualChecklistComplete'])
        self.report['records'][key]={'result':'Pass','notes':'Keep these older notes','caseSha256':'0'*64,'updatedUtc':'2026-11-02T09:00:00Z'}
        r=qa.assess(self.report,self.spec);self.assertEqual(r['counts']['Desactualizado'],1)
        self.assertFalse(r['manualChecklistComplete']);self.assertEqual(self.report['records'][key]['notes'],'Keep these older notes')

    def test_unconfirmed_environment_and_non_boolean_are_distinct(self):
        self.report['environment']['candidateConfirmed']=False
        self.assertFalse(qa.assess(self.report,self.spec)['manualChecklistComplete'])
        for value in ['true',1,None]:
            self.report['environment']['candidateConfirmed']=value
            with self.subTest(value=value),self.assertRaises(ValueError):qa.assess(self.report,self.spec)

    def test_untrusted_notes_are_escaped_in_generated_markup(self):
        definition=copy.deepcopy(self.spec);definition['cases'][0]['title']='</summary><script>unsafe()</script>'
        text=qa.render(definition)
        self.assertNotIn('<script>unsafe()',text);self.assertIn('&lt;script&gt;unsafe()',text)
        self.assertNotIn('innerHTML',text)

    def test_json_duplicates_rejected_without_coercion(self):
        with self.assertRaisesRegex(ValueError,'duplicate_key'):qa.strict_load('{"format":"old","format":"new"}')
        self.report['records'][next(iter(self.report['records']))]['result']=True
        with self.assertRaises(ValueError):qa.assess(self.report,self.spec)

    def test_selection_does_not_mutate_catalogue(self):
        path=ROOT/'docs/QA-CASOS-WASCAR.json';before=path.read_bytes();qa.outputs()
        self.assertEqual(path.read_bytes(),before);self.assertEqual(len(self.spec['cases']),14)

if __name__=='__main__':unittest.main()
