from unittest import TestCase

from mattersyn_simple import checked_sheet_thickness, public_document, sheet_thickness_measurement
from to_site import measurement_display_fields


class CheckedSheetThicknessTests(TestCase):
    def structure(self, quote, value=4, shape='nanosheets', unit='nm', page=4):
        return {'shape': {'value': shape},
                'size_method': {'value': 'AFM'},
                'size': {'value': value, 'unit': unit, 'page': page, 'quote': quote}}

    def test_endpoint_preserved_without_adding_upper_endpoint(self):
        st = self.structure('Thickness for sample A-8 ranges from 4–11 nm.')
        desc = checked_sheet_thickness(st)
        self.assertEqual(desc, ('nanosheet_thickness_lower_endpoint', False))
        m = {'property': 'diameter', 'technique': 'not reported',
             'value': {'value': 4, 'unit': 'nm', 'maximum': None, 'evidence': [{'locator': 'p.4'}]}}
        fixed = sheet_thickness_measurement(st, m, desc)
        self.assertEqual(fixed['value']['value'], 4)
        self.assertIsNone(fixed['value']['maximum'])
        self.assertEqual(fixed['value']['evidence'], m['value']['evidence'])
        self.assertEqual(fixed['technique'], 'AFM')
        self.assertEqual(measurement_display_fields(fixed)['label'], 'Nanosheet thickness (lower endpoint)')
        self.assertEqual(m['property'], 'diameter')

    def test_approximate_thickness_remains_quote_free(self):
        st = self.structure('The sheets were approximately 2.7 nm thick.', 2.7)
        self.assertEqual(checked_sheet_thickness(st), ('nanosheet_thickness', True))
        source = {'values_kept': 3, 'pairs': [{'product': 'sheet-A', 'structure': st}]}
        out = public_document(source)
        self.assertEqual(out['values_kept'], 3)
        self.assertEqual(out['pairs'][0]['structure']['size'],
                         {'value': 2.7, 'unit': 'nm', 'page': 4,
                          'dimension': 'nanosheet_thickness', 'approximate': True})
        self.assertIn('quote', source['pairs'][0]['structure']['size'])

    def test_mixed_or_unbound_text_does_not_relabel_sizes(self):
        for quote, extra in [
            ('Thickness 4 nm; diameter 18 nm.', {}),
            ('Lateral size 4 nm.', {}),
            ('The thickness is described separately. The sample was 4 nm.', {}),
            ('The thickness was 14 to 20 nm.', {}),
            ('It was 3–4 nm thick.', {}),
            ('It was 4 nm thick.', {'shape': 'nanorods'}),
            ('It was 4 nm thick.', {'unit': 'µm'}),
            ('It was 4 nm thick.', {'page': None}),
        ]:
            with self.subTest(quote=quote, extra=extra):
                self.assertIsNone(checked_sheet_thickness(self.structure(quote, **extra)))
