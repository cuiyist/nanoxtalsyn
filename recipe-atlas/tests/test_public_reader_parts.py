import base64,copy,hashlib,importlib.util,json,subprocess,sys,unittest,uuid
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'scripts'))
import public_reader_registry as m
import reader_presentation_registry as source

def value():
 return {'schema_version':'1.0','records':{f'r{i}':{'status':'source_extracted','training_eligible':False,'figures':[{'id':f'f{i}','public_caption':'short factual paraphrase '+str(i),'origin':'manual','status':'accepted','full_crop_sha256':'a'*64}],'padding':'x'*160}for i in range(8)},'materials':{'m':{'record_ids':['r0'],'component_only':True}},'figures_by_source':{},'counter':9}
def merge(parts):
 return m.load_public_parts(parts[m.BASE],parts.__getitem__)
class PublicParts(unittest.TestCase):
 def test_current_unsplit_preserves_exact_legacy_bytes(self):
  v=value();raw=(json.dumps(v,indent=2)+'\n').encode();self.assertEqual(m.public_parts(v,raw),{m.BASE:raw});self.assertEqual(merge(m.public_parts(v,raw)),v)
 def test_forced_small_split_is_deterministic_exact_and_disjoint(self):
  v=value();before=copy.deepcopy(v);limit=int(len(m.encoded(v))*.8)
  with patch.object(m,'MAX_PART_BYTES',limit):first=m.public_parts(v);second=m.public_parts(v)
  self.assertEqual(first,second);self.assertEqual(set(first),{m.BASE,m.PART});self.assertTrue(all(len(b)<limit for b in first.values()));self.assertEqual(merge(first),v);self.assertEqual(v,before)
  a=json.loads(first[m.BASE]);b=json.loads(first[m.PART]);self.assertEqual(a[source.MARKER]['part'],m.PART)
  for table in source.TABLES:self.assertFalse(set(a[table])&set(b[table]))
 def test_exact_public_limit_splits_instead_of_emitting_equal_limit(self):
  v=value();limit=len(m.encoded(v))
  with patch.object(m,'MAX_PART_BYTES',limit):parts=m.public_parts(v)
  self.assertEqual(set(parts),{m.BASE,m.PART});self.assertTrue(all(len(b)<limit for b in parts.values()))
 def test_one_indivisible_oversized_entry_fails(self):
  v={'records':{'r':{'caption':'x'*2000}},'materials':{},'figures_by_source':{}}
  with patch.object(m,'MAX_PART_BYTES',400),self.assertRaisesRegex(ValueError,'below80MiB'):m.public_parts(v)
 def test_bad_tables_reserved_marker_and_wrong_legacy_bytes_fail(self):
  for key in source.TABLES:
   v=value();v[key]=[]
   with self.assertRaises(ValueError):m.public_parts(v)
  v=value();v[source.MARKER]={}
  with self.assertRaises(ValueError):m.public_parts(v)
  with self.assertRaises(ValueError):m.public_parts(value(),b'{}')
 def test_source_split_code_and_unsplit_contract_unchanged(self):
  self.assertEqual(m.MAX_PART_BYTES,80*1024*1024);self.assertEqual(merge(m.public_parts(value())),value())
 def test_three_or_more_parts_preserve_unicode_order_and_unknown_metadata(self):
  v=value();v['unknown']={'retained':True};v['records']['r0']['unicode']=('µm"'+chr(10)+chr(92))*15
  before=copy.deepcopy(v)
  with patch.object(m,'MAX_PART_BYTES',1500):
   parts=m.public_parts(v);self.assertEqual(parts,m.public_parts(v));self.assertEqual(merge(parts),v)
   self.assertTrue(all(len(raw)<1500 for raw in parts.values()))
  marker=json.loads(parts[m.BASE])[source.MARKER]
  self.assertEqual(marker['schema'],m.MULTIPART_SCHEMA);self.assertGreaterEqual(len(marker['parts']),3)
  actual=merge(parts)
  for table in source.TABLES:self.assertEqual(list(actual[table]),list(v[table]))
  self.assertEqual(before,v)
 def test_actual_source_partition_overflow_uses_bounded_public_parts(self):
  with patch.object(source,'MAX_PART_BYTES',1500),patch.object(m,'MAX_PART_BYTES',1500):
   parts=m.public_parts(value());self.assertEqual(merge(parts),value())
  self.assertGreater(len(parts),2)
 def test_bad_multipart_markers_fail_before_reading_any_part(self):
  ref={'part':m.PART,'sha256':'a'*64}
  invalid=[None,{}, {'schema':m.MULTIPART_SCHEMA,'parts':[]},
   {'schema':m.MULTIPART_SCHEMA,'parts':[ref,ref]},
   {'schema':m.MULTIPART_SCHEMA,'parts':[{'part':'../private.json','sha256':'a'*64}]},
   {'schema':m.MULTIPART_SCHEMA,'parts':[{'part':m.PART,'sha256':'bad'}]},
   {'schema':m.MULTIPART_SCHEMA,'parts':[dict(ref,extra=1)]},
   {'schema':m.MULTIPART_SCHEMA,'parts':[ref],'extra':1},
   {'schema':m.MULTIPART_SCHEMA,'parts':[ref]*(m.MAX_PARTS+1)}]
  for marker in invalid:
   with self.subTest(marker=str(marker)[:80]):
    def forbidden(name):self.fail('Invalid marker read a secondary part')
    with self.assertRaises(ValueError):m.load_public_parts(m.encoded({**value(),source.MARKER:marker}),forbidden)
 def test_missing_corrupt_and_duplicate_later_parts_fail_closed(self):
  with patch.object(m,'MAX_PART_BYTES',1500):parts=m.public_parts(value())
  base=json.loads(parts[m.BASE]);refs=base[source.MARKER]['parts'];name=refs[-1]['part']
  missing={k:v for k,v in parts.items() if k!=name}
  with self.assertRaises(KeyError):merge(missing)
  with self.assertRaisesRegex(ValueError,'checksum'):merge({**parts,name:parts[name]+b' '})
  changed=json.loads(parts[name]);changed['records']['r0']=value()['records']['r0'];raw=m.encoded(changed)
  refs[-1]['sha256']=hashlib.sha256(raw).hexdigest()
  with self.assertRaisesRegex(ValueError,'Duplicate'):merge({**parts,m.BASE:m.encoded(base),name:raw})
 def test_shard_loader_reads_all_parts_with_exact_shard_objects(self):
  import tempfile
  from build_reader_shards import load_public_view,shards
  with patch.object(m,'MAX_PART_BYTES',1500):parts=m.public_parts(value())
  with tempfile.TemporaryDirectory(prefix='reader-multipart-') as tmp:
   root=Path(tmp)
   for name,raw in parts.items():(root/name).write_bytes(raw)
   actual=load_public_view(root);self.assertEqual(actual,value())
   for rid,entry in value()['records'].items():self.assertEqual(json.loads(shards(actual)['records/'+rid+'.json']),entry)
 def test_python_multipart_bytes_load_in_browser_without_semantic_changes(self):
  with patch.object(m,'MAX_PART_BYTES',1500):parts=m.public_parts(value())
  loader=(HERE.parent/'static/reader-presentation-loader.mjs').as_uri()
  script="""
import fs from 'node:fs';import assert from 'node:assert/strict';import {webcrypto} from 'node:crypto';
const {createReaderPresentationLoader}=await import(process.argv[1]);
const payload=JSON.parse(fs.readFileSync(0,'utf8'));let calls=0;
const load=createReaderPresentationLoader({crypto:webcrypto,fetcher:async url=>{
 calls++;const raw=Buffer.from(payload.parts[new URL(url).pathname.split('/').at(-1)],'base64');
 return {ok:true,arrayBuffer:async()=>Uint8Array.from(raw).buffer};
}});
assert.deepEqual(await load('https://example.test/data/reader-presentation.json'),payload.expected);
assert.equal(calls,Object.keys(payload.parts).length);
"""
  payload={'parts':{k:base64.b64encode(raw).decode()for k,raw in parts.items()},'expected':value()}
  result=subprocess.run(['node','--input-type=module','-e',script,loader],input=json.dumps(payload),text=True,capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr)
 def test_oversized_metadata_or_received_file_fails_without_truncation(self):
  v=value();v['opaque_metadata']='x'*2000
  with patch.object(m,'MAX_PART_BYTES',1500),self.assertRaisesRegex(ValueError,'below80MiB'):m.public_parts(v)
  raw=m.encoded(value())
  with patch.object(m,'MAX_PART_BYTES',len(raw)),self.assertRaisesRegex(ValueError,'below80MiB'):m.load_public_parts(raw,lambda name:b'')
 def test_normal_builder_uses_small_fixture_and_preserves_display_semantics(self):
  spec=importlib.util.spec_from_file_location('private_candidate_reader_builder',HERE.parent/'scripts/build_reader_metadata.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
  root=HERE.parents[2]/'fixtures'/('reader-'+uuid.uuid4().hex);(root/'data/records').mkdir(parents=True);(root/'dist/data/materials').mkdir(parents=True)
  v=value()
  for rid in v['records']:
   v['records'][rid].update(source_id='s',scopeLabel='Source extracted scope')
   (root/'data/records'/(rid+'.json')).write_text(json.dumps({'lineage':{'source_group':'s'}}),encoding='utf-8')
  # Exercise unchanged asset-display transformation BEFORE physical splitting.
  import asset_display,hashlib
  fig=v['records']['r0']['figures'][0];fig.update(public_asset='assets/withheld.png',public_asset_sha256='a'*64)
  card=b'<svg/>';cardpath=root/'dist/assets/source-links/card.svg';cardpath.parent.mkdir(parents=True);cardpath.write_bytes(card)
  row={'original_path':'assets/withheld.png','original_sha256':'a'*64,'display_path':'assets/source-links/card.svg','display_sha256':hashlib.sha256(card).hexdigest(),'source_url':'https://doi.org/example','display_note':'Source link only'}
  (root/'private-build').mkdir();(root/'private-build/asset-display-overrides.json').write_text(json.dumps({'schema':'mattersyn-asset-display-overrides/1','scope':'private_build_input_do_not_deploy','assets':[row]}),encoding='utf-8')
  expected=asset_display.transform(v,{row['original_path']:row},[])
  # Normal builder requires the authored library; tiny fixtures carry it too.
  import reader_background
  (root/'scripts').mkdir()
  for relative in ['data/reader-background-library.json','scripts/reader_background_reference_pins.json']:
   (root/relative).write_bytes((HERE.parent/relative).read_bytes())
  fixture_records={rid:{'lineage':{'source_group':'s'}}for rid in v['records']}
  expected,coverage=reader_background.attach_background(expected,fixture_records,reader_background.load_library(root))
  (root/'data/reader-presentation-reviewed.json').write_text(json.dumps(v),encoding='utf-8');(root/'dist/data/materials/m.json').write_text(json.dumps({'record_ids':['r0']}),encoding='utf-8')
  builder.ROOT=root
  with patch.object(m,'MAX_PART_BYTES',int(len(m.encoded(expected))*.8)):builder.main()
  parts={n:(root/'dist/data'/n).read_bytes()for n in [m.BASE,m.PART]};actual=merge(parts);self.assertEqual(actual,expected)
  self.assertEqual(actual['records']['r0']['status'],'source_extracted');self.assertFalse(actual['records']['r0']['training_eligible']);self.assertEqual(actual['records']['r0']['figures'][0]['origin'],'manual');self.assertEqual(actual['counter'],v['counter']);self.assertEqual(actual['records']['r0']['figures'][0]['display_kind'],'source_link')
if __name__=='__main__':unittest.main()
