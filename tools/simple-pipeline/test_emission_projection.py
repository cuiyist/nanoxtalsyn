"""Only discard the exact excitation or vibrational value mislabeled as PL."""
import copy
import unittest

from mattersyn_simple import has_misattributed_emission_peak, public_document


def fact(value, unit, quote, page=2):
    return {'emission_peak': {'value': value, 'unit': unit, 'quote': quote, 'page': page}}


class EmissionProjectionTests(unittest.TestCase):
    def test_vibrational_units_and_context(self):
        for unit in ('cm−1', 'cm⁻¹', 'cm^-1', 'CM -1'):
            with self.subTest(unit=unit):
                self.assertTrue(has_misattributed_emission_peak(
                    fact(1500, unit, 'The infrared band at 1500 cm^-1 was assigned to a vibration.')))

    def test_laser_value_not_separate_emission(self):
        text = 'With 710 nm semiconductor laser excitation, the photoluminescence peaked at 960 nm.'
        self.assertTrue(has_misattributed_emission_peak(fact(710, 'nm', text)))
        self.assertTrue(has_misattributed_emission_peak(
            fact(710, 'nm', 'Emission recorded with 710 nm (4 W/cm², p. w.) laser excitation.')))
        self.assertFalse(has_misattributed_emission_peak(fact(960, 'nm', text)))
        self.assertFalse(has_misattributed_emission_peak(fact(71, 'nm', text)))

    def test_preserve_unsettled_and_explicit_luminescence(self):
        self.assertFalse(has_misattributed_emission_peak(
            fact(8500, 'cm⁻¹', 'Photoluminescence was observed in a band at 8500 cm⁻¹.')))
        self.assertFalse(has_misattributed_emission_peak(fact(800, 'nm', 'A band at 800 nm was observed.')))
        self.assertFalse(has_misattributed_emission_peak(
            fact(710, 'nm', '710 nm laser excitation', page=None)))

    def test_projection_does_not_edit_checked_evidence(self):
        structure = fact(710, 'nm', 'Measurements used 710 nm laser excitation.')
        structure['phase'] = {'value': 'cubic', 'page': 3, 'quote': 'cubic phase'}
        original = {'values_kept': 2, 'pairs': [{'structure': structure}]}
        before = copy.deepcopy(original)
        export = public_document(original)
        self.assertEqual(original, before)
        self.assertEqual(export['values_kept'], 1)
        self.assertEqual(export['pairs'][0]['structure'], {'phase': {'value': 'cubic', 'page': 3}})


if __name__ == '__main__':
    unittest.main()
