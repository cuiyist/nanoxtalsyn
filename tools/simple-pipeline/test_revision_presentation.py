import copy
import unittest
from revision_presentation import rebind_record_refs,append_measurements,rebind_protocol


class Tests(unittest.TestCase):
    def test_exact_hash_only(self):
        old={'figure':{'caption':'Authored fixture','source':{'data_path':'data/records/a.json','input_sha256':'old','json_pointer':'/products'}},'other':{'input_sha256':'old'}}
        before=copy.deepcopy(old)
        new,count=rebind_record_refs(old,{'data/records/a.json':('old','new')})
        self.assertEqual(count,1);self.assertEqual(old,before)
        self.assertEqual(new['other'],old['other']);self.assertEqual(new['figure']['caption'],old['figure']['caption'])
    def test_stale_hash_rejected(self):
        with self.assertRaises(ValueError):rebind_record_refs({'data_path':'x','input_sha256':'wrong'},{'x':('old','new')})
    def test_append_exact_measurement_keep_old_display(self):
        old={'record_id':'a','measurements':[]}
        m={'id':'new','property':'photoluminescence_peak','technique':'PL','sample_id':'a--sample',
           'value':{'value':500,'unit':'nm','status':'reported'},'evidence':[{'source_id':'s','locator':'Main PDF p.2'}]}
        view={'figures':[{'id':'fixture'}],'productFacts':[{'value':'old'}],'allProductFacts':[{'value':'old'}],'scopeLabel':'Keep'}
        before=copy.deepcopy(view);new,added=append_measurements(view,old,dict(old,measurements=[m]),'hash')
        self.assertEqual(view,before);self.assertEqual(new['figures'],view['figures']);self.assertEqual(new['scopeLabel'],'Keep')
        self.assertEqual(added,['new']);self.assertEqual(new['allProductFacts'][0],{'value':'old'})
        self.assertEqual(new['allProductFacts'][1]['source']['json_pointer'],'/measurements/0/value')
        self.assertEqual(new['allProductFacts'][1]['value'],'500 nm')
    def test_unknown_measurement_not_promoted(self):
        old={'record_id':'a','measurements':[]};new=dict(old,measurements=[{'id':'n','value':{'value':None,'status':'not_reported'}}])
        with self.assertRaises(ValueError):append_measurements({},old,new,'hash')
    def test_protocol_figures_and_operation_ids_preserved(self):
        old={'record_id':'a'};new={'record_id':'a','operations':[{'id':'s1'},{'id':'s2'}]}
        binding={'record_id':'a','source_record_sha256':'old','bindings':[{'operation_id':'s1','asset_path':'fixture.svg'}]}
        result=rebind_protocol(binding,old,new,'old','new')
        self.assertEqual(result['bindings'],binding['bindings']);self.assertEqual(binding['source_record_sha256'],'old')

if __name__=='__main__':unittest.main()
