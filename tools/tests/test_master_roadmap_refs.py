"""Catalog references stay unweighted and never expand the closure ledger."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('master_roadmap',ROOT/'tools/build_master_roadmap.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class RoadmapReferencesTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads(m.CONFIG.read_text(encoding='utf-8'))

    def build(self,config):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'config.json';p.write_text(json.dumps(config),encoding='utf-8')
            with patch.object(m,'CONFIG',p):return m.build()

    def test_declared_catalog_owner_preserves_ledger_and_credit(self):
        ledger=ROOT/'docs/PLAN-CIERRE-RACKCLICK.json';before=ledger.read_bytes()
        outputs,registry=self.build(self.config)
        self.assertTrue(outputs);self.assertEqual(before,ledger.read_bytes())
        serialized=json.dumps(registry)
        self.assertIn('C-HW-02',serialized)
        # Compare to the same config with the observation using ledger IDs:
        # neither the ledger nor its closure statistics may depend on that link.
        alternate=copy.deepcopy(self.config)
        observation=next(x for x in alternate['observations'] if x['id']=='REQ-HW-MOUNT-01')
        observation.update(owner='I-04',related=[])
        _,other=self.build(alternate)
        self.assertEqual(registry['metric'],other['metric'])

    def test_unknown_owner_still_rejected(self):
        self.config['observations'][0]['owner']='unknown-result'
        with self.assertRaisesRegex(ValueError,'invalid_observation_owner'):self.build(self.config)

    def test_unknown_related_result_still_rejected(self):
        self.config['observations'][0]['related']=['unknown-result']
        with self.assertRaisesRegex(ValueError,'invalid_related_result'):self.build(self.config)


if __name__=='__main__':unittest.main()
