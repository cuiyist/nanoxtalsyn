"""Synthetic same-source, distinct-step numeric attribution regressions."""
from copy import deepcopy
import unittest
from unittest.mock import patch

import completeness_numbers as numbers


class NumericCarrierTest(unittest.TestCase):
    def test_overlap_does_not_loan_a_number_from_a_different_step(self):
        quote='The synthetic mixture was sonicated and subsequently reheated to 140 degrees C.'
        recorded={'action':'sonicate','quote':quote,'uses':[]}
        separate={'action':'reheat','quote':quote,'temperature':140,'temperature_unit':'C','uses':[]}
        a={'structure':{},'recipe':{'steps':[recorded,separate]}}
        b={'structure':{},'recipe':{'steps':[{**recorded,'action':'sonication'},separate]}}
        kept={'structure':{},'recipe':{'chemicals':[],'steps':[deepcopy(recorded),deepcopy(separate)]}}
        def check():
            with patch.object(numbers,'check',side_effect=lambda *_:[deepcopy(kept)]), \
                 patch.object(numbers.e,'match_pairs',return_value=[(a,b)]):
                return numbers.check_v6('[page 1]\n'+quote,{'pairs':[a]},{'pairs':[b]})[0]['recipe']['steps']
        self.assertNotIn('temperature',check()[0])
        self.assertEqual(check()[1]['temperature'],140)
        a['recipe']['steps'][0]={**recorded,'temperature':140,'temperature_unit':'C'}
        self.assertEqual(check()[0]['temperature'],140)


if __name__=='__main__':unittest.main()
