import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'recipe-atlas/scripts'))
import reader_presentation_registry as legacy
import public_reader_registry as public
sys.path.insert(0,str(HERE))
import reader_source_multipart as new


def sample():
    return {'schema':'opaque-fixture','unknown':{'order':['z','a'],'values':[1.0,1e-7,9007199254740993,None,False]},
            'records':{f'r{i}':{'review_status':'source_reviewed' if i%2 else 'source_extracted',
                               'caption':'µ'*550,'training_eligible':False} for i in range(12)},
            'materials':{'m':{'record_ids':['r11','r0']}},
            'figures_by_source':{'s':{'rights':'unverified','asset_sha256':'a'*64}}}


class SourceMultipartTests(unittest.TestCase):
    def setUp(self):
        self.patch=patch.object(legacy,'MAX_PART_BYTES',4096);self.patch.start();self.addCleanup(self.patch.stop)
        self.value=sample()

    def decode(self,payloads):
        return new.decode_source_parts(payloads[legacy.BASE],payloads.__getitem__,list(payloads)[1:])

    def test_legacy_two_part_bytes_are_identical(self):
        small={**self.value,'records':{'r':self.value['records']['r0']}}
        self.assertEqual(new.source_parts(small,True),legacy.serialized_parts(small,True))

    def test_overflow_preserves_all_values_and_order(self):
        before=copy.deepcopy(self.value);parts=new.source_parts(self.value,True)
        self.assertGreater(len(parts),2)
        self.assertTrue(all(len(raw)<=4096 for raw in parts.values()))
        after=self.decode(parts)
        self.assertEqual(after,before);self.assertEqual(self.value,before)
        for name in legacy.TABLES:self.assertEqual(list(after[name]),list(before[name]))
        self.assertEqual(list(after),list(before))

    def test_legacy_serializer_still_refuses_overflow(self):
        with self.assertRaisesRegex(ValueError,'Two Reader source parts exceed'):
            legacy.serialized_parts(self.value,True)

    def test_corrupt_or_missing_secondary_rejected(self):
        parts=new.source_parts(self.value,True)
        parts[legacy.PART]+=b' '
        with self.assertRaisesRegex(ValueError,'checksum'):self.decode(parts)
        parts=new.source_parts(self.value,True);parts.pop(legacy.PART)
        with self.assertRaisesRegex(ValueError,'Missing or orphan'):self.decode(parts)

    def test_nonsequential_duplicate_traversal_and_bad_digest_rejected(self):
        parts=new.source_parts(self.value,True);original=json.loads(parts[legacy.BASE])
        for field,value in [('part','../outside.json'),('part','reader-presentation-reviewed.part8.json'),('sha256','bad')]:
            doc=copy.deepcopy(original);doc[legacy.MARKER]['parts'][0][field]=value
            with self.assertRaises(ValueError):new.part_refs(doc[legacy.MARKER])
        marker=copy.deepcopy(original[legacy.MARKER]);marker['parts'][1]=marker['parts'][0]
        with self.assertRaises(ValueError):new.part_refs(marker)

    def test_duplicate_logical_key_rejected_even_with_correct_hashes(self):
        parts=new.source_parts(self.value,True);doc=json.loads(parts[legacy.BASE])
        first=json.loads(parts[legacy.PART]);second_name=doc[legacy.MARKER]['parts'][1]['part']
        second=json.loads(parts[second_name]);key=next(iter(first['records']))
        second['records'][key]={};parts[second_name]=legacy._encoded(second)
        doc[legacy.MARKER]['parts'][1]['sha256']=hashlib.sha256(parts[second_name]).hexdigest()
        parts[legacy.BASE]=legacy._encoded(doc)
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.decode(parts)

    def test_indivisible_entry_and_metadata_overflow_rejected(self):
        value={**self.value,'records':{'huge':'x'*5000}}
        with self.assertRaisesRegex(ValueError,'Indivisible'):new.source_parts(value,True)
        value={**self.value,'unknown':'x'*5000}
        with self.assertRaisesRegex(ValueError,'metadata/index'):new.source_parts(value,True)

    def test_shrink_retains_all_existing_paths_and_writes_primary_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data'/legacy.BASE;new.write_source(path,self.value,True)
            original=new.inspect_source(path)[0];names=[p.name for p in original]
            small={**self.value,'records':{'r':{}},'materials':{},'figures_by_source':{}}
            calls=[];real=new.os.replace
            def replace(src,dst):calls.append(Path(dst).name);return real(src,dst)
            with patch.object(new.os,'replace',replace):new.write_source(path,small)
            self.assertEqual([p.name for p in new.inspect_source(path)[0]],names)
            self.assertEqual(calls[-1],legacy.BASE)
            self.assertEqual(new.load_source(path),small)
            with self.assertRaisesRegex(ValueError,'collapse'):new.write_source(path,small,False)

    def test_orphan_and_interrupted_writes_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data'/legacy.BASE;new.write_source(path,self.value,True)
            orphan=path.with_name('reader-presentation-reviewed.part99.json');orphan.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'orphan'):new.load_source(path)
            orphan.unlink()
            changed=copy.deepcopy(self.value);changed['records']['r0']['caption']='changed'
            real=new.os.replace;calls=[]
            def interrupted(src,dst):
                calls.append(dst)
                if len(calls)==2:raise OSError('fixture interruption')
                return real(src,dst)
            with patch.object(new.os,'replace',interrupted),self.assertRaises(OSError):new.write_source(path,changed)
            with self.assertRaises(ValueError):new.load_source(path)

    def test_invalid_counts_marker_and_extra_fields_rejected(self):
        for count in (0,True,1025):
            with self.assertRaises(ValueError):new.source_parts(self.value,True,count)
        value={**self.value,legacy.MARKER:{}}
        with self.assertRaisesRegex(ValueError,'Reserved'):new.source_parts(value,True)
        marker={'schema':new.SCHEMA,'parts':[]}
        with self.assertRaises(ValueError):new.part_refs(marker)

    def test_legacy_and_single_loads_preserve_existing_contract(self):
        small={**self.value,'records':{},'materials':{},'figures_by_source':{}}
        for split in (False,True):
            parts=legacy.serialized_parts(small,split)
            self.assertEqual(self.decode(parts),small)

    def test_public_serializer_contract_is_unchanged(self):
        small={**self.value,'records':{},'materials':{},'figures_by_source':{}}
        before=public.public_parts(small)
        new.source_parts(self.value,True)
        self.assertEqual(public.public_parts(small),before)

    def test_explicit_legacy_bytes_stay_exact_but_cannot_bypass_bound(self):
        small={**self.value,'records':{},'materials':{},'figures_by_source':{}}
        raw=json.dumps(small,ensure_ascii=False,indent=2).replace('\n','\r\n').encode()
        self.assertEqual(new.source_parts(small,legacy_raw=raw),{legacy.BASE:raw})
        oversized=raw+b' '*4096
        parts=new.source_parts(small,legacy_raw=oversized)
        self.assertGreater(len(parts),1)
        self.assertEqual(self.decode(parts),small)
        with self.assertRaisesRegex(ValueError,'differ'):
            new.source_parts(small,legacy_raw=b'{}')

    def test_single_file_partial_tables_and_original_format_remain_compatible(self):
        value={'records':{'r':{}},'figures_by_source':{}}
        raw=json.dumps(value,indent=2).replace('\n','\r\n').encode()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data'/legacy.BASE
            new.write_source(path,value,legacy_raw=raw)
            self.assertEqual(path.read_bytes(),raw)
            self.assertEqual(new.load_source(path),value)
        with self.assertRaisesRegex(ValueError,'tables'):
            new.source_parts(value,True)


if __name__=='__main__':unittest.main()
