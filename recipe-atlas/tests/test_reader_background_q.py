import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
ATLAS=HERE.parent
sys.path.append(str(ATLAS/'scripts'))
from reader_background_q import choose,identity_projection,select_q_background,validated


class QNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library=validated(json.loads((ATLAS/'data/reader-background-q.json').read_bytes()))

    def test_krueger_prioritizes_exact_growth_chemistry_above_purification(self):
        record=json.loads((ATLAS/'data/records/krueger2005-cdse-ac0481912-ode-dots.json').read_bytes())
        before=json.dumps(record,sort_keys=True)
        cards=select_q_background(record,{},self.library,identity_projection(ATLAS))
        assert len(cards)==4
        self.assertEqual({x['id'] for x in cards[:3]},{'cdo-oleic-acid','selenium-top','ode-solvent'})
        self.assertNotIn('thiol-source-and-ligand',{x['id'] for x in cards})
        self.assertEqual(len({x['topic'] for x in cards}),len(cards))
        self.assertTrue(all(x['label']==self.library['label'] for x in cards))
        self.assertEqual(json.dumps(record,sort_keys=True),before)

    def test_no_exact_match_has_only_previous_fallback(self):
        items=choose(self.library,{'cid:99999999999'},'Not reported')
        self.assertEqual([r['id'] for r in items],['general-context'])
