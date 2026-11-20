import unittest
from continued_particle_roles import context,override
from starting_particle_roles import revise


def material(n,role='reagent',formula=None):
    return {'name':n,'role':role,'formula':formula}


def record(rows,method='liquid heat-up',steps=None):
    return {'material':{'formula':'InAs','components':['InAs'],'elements':['In','As']},
            'method':method,'materials':rows,'operations':steps or []}


class W78(unittest.TestCase):
    def test_growth_method_changes_bare_formula_but_not_named_particles(self):
        rows=[material('InAs','starting_particles'),material('InAs quantum dots')]
        c=context(record(rows,'Molecular-beam epitaxy'))
        self.assertEqual(override(rows[0],c),('W7_grown_layer','grown_layer'))
        self.assertIsNone(override(rows[1],c))

    def test_substrate_is_only_reported_name_or_explicit_phrase(self):
        rows=[material('GaAs'),material('GaAs buffer')]
        c=context(record(rows,'CVD'))
        self.assertIsNone(override(rows[0],c,['GaAs was grown.']))
        self.assertEqual(override(rows[0],c,['on a GaAs (100) substrate.']),('W7_substrate','substrate'))
        self.assertEqual(override(rows[1],c),('W7_substrate','substrate'))

    def test_nonvapor_only_omit_bare_whole_product_with_checked_precursor(self):
        rows=[material('InAs'),material('indium acetate','metal_precursor','In(C2H3O2)3'),
              material('InAs nanocrystals','starting_particles')]
        c=context(record(rows));self.assertTrue(c['precursors'])
        self.assertEqual(override(rows[0],c),('W8',None))
        self.assertIsNone(override(rows[2],c))
        unknown=context(record([rows[0],material('zinc acetate','metal_precursor','Zn(C2H3O2)2')]))
        self.assertIsNone(override(rows[0],unknown))

    def test_growth_may_be_in_step_without_method(self):
        r=record([material('InAs')],steps=[{'description':'Use Stranski–Krastanov growth.'}])
        self.assertEqual(override(r['materials'][0],context(r)),('W7_grown_layer','grown_layer'))

    def test_full_converter_keeps_layer_amount_and_holds_product_amount(self):
        def filled(n,role='reagent',quant=None):
            return {**material(n,role),'id':n,'quantities':quant or {},
                    'evidence':[],'identity':{},'notes':[]}
        layer=filled('InAs','starting_particles',{'amount':{'value':2}})
        precursor=filled('indium acetate','metal_precursor')
        def complete(r):
            return {**r,'quality':{'review_status':'source_extracted'},'stocks':[],
                    'material_states':[],'condition_options':[]}
        a,ledger=revise(complete(record([layer],'MBE')))
        self.assertEqual(a['materials'][0]['role'],'grown_layer')
        self.assertEqual(a['materials'][0]['quantities'],layer['quantities'])
        self.assertEqual(ledger['counts'],{'W7_grown_layer':1})
        _,ledger=revise(complete(record([layer,precursor])))
        self.assertTrue(ledger['holds'])
        self.assertEqual(ledger['holds'][0][0],'W8_quantity')


if __name__=='__main__':unittest.main()
