"""Tiny fixtures exercise the real Source writers and importer/preflight code.

No full build, real record change, scientific approval or network access.
"""
import ast
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_source_reader_multipart import legacy, new, public, sample, REPO


def module(name,relative):
    sys.path.insert(0,str((REPO/relative).parent))
    spec=importlib.util.spec_from_file_location(name,REPO/relative)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


converter=module('multipart_converter','tools/simple-pipeline/to_site.py')
captions=module('multipart_captions','tools/simple-pipeline/local_caption_backfill.py')
importer=module('multipart_importer','tools/package-importer/importer.py')


def assignment(relative,name):
    tree=ast.parse((REPO/relative).read_text(encoding='utf8'))
    found=[node for node in ast.walk(tree) if isinstance(node,ast.Assign)
           and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
           and node.targets[0].id==name]
    if len(found)!=1:raise AssertionError('Expected one actual assignment: '+name)
    return found[0]


def execute(nodes,scope):
    code=compile(ast.fix_missing_locations(ast.Module(body=copy.deepcopy(nodes),type_ignores=[])),
                 '<native-source-consumer-fixture>','exec')
    exec(code,scope)
    return scope


class SourceConsumerTests(unittest.TestCase):
    def setUp(self):
        bounded=patch.object(legacy,'MAX_PART_BYTES',4096)
        bounded.start();self.addCleanup(bounded.stop)

    def test_native_converter_and_caption_writer_preserve_all_parts_and_canonical_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data'/legacy.BASE;path.parent.mkdir()
            record=path.parent/'canonical.json';raw=b'{"value":1.000,"training":false}\n'
            record.write_bytes(raw);value=sample()
            converter.dump_like(path,value)
            count=len(legacy.source_paths(path));self.assertGreater(count,2)
            self.assertEqual(legacy.load_reviewed_reader(path),value)
            changed=copy.deepcopy(value);changed['records']['r11']['caption']='new fixture caption'
            captions.write(path,changed)
            self.assertEqual(legacy.load_reviewed_reader(path),changed)
            self.assertGreaterEqual(len(legacy.source_paths(path)),count)
            self.assertTrue(all(p.stat().st_size<=4096 for p in legacy.source_paths(path)))
            self.assertEqual(record.read_bytes(),raw)

    def test_exact_source_path_keeps_legacy_crlf_and_optional_final_newline(self):
        value={**sample(),'records':{}}
        for ending in ('\r\n',''):
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'data'/legacy.BASE;path.parent.mkdir()
                original=json.dumps(value,ensure_ascii=False,indent=2).replace('\n','\r\n')+ending
                path.write_bytes(original.encode())
                converter.dump_like(path,value)
                expected=json.dumps(value,ensure_ascii=False,separators=(',',':'))+ending
                self.assertEqual(path.read_bytes(),expected.encode())
                self.assertEqual(len(legacy.source_paths(path)),1)

    def test_corrupt_last_part_rejected_by_both_native_writers(self):
        for writer in (converter.dump_like,captions.write):
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'data'/legacy.BASE;value=sample()
                legacy.write_reviewed_reader(path,value)
                parts=legacy.source_paths(path);parts[-1].write_bytes(parts[-1].read_bytes()+b' ')
                before={p.name:p.read_bytes() for p in parts}
                with self.assertRaisesRegex(ValueError,'checksum'):writer(path,value)
                self.assertEqual(before,{p.name:p.read_bytes() for p in parts})

    def test_actual_importer_serialization_preserves_every_source_part_and_single_bytes(self):
        node=assignment('tools/package-importer/importer.py','reader_payloads')
        for value,parts in (({**sample(),'records':{}},['primary']),
                            (sample(),['primary','part2']),
                            ({**sample(),'records':{}},['primary','part2','part3','part4'])):
            scope=execute([node],{'reader_merged':value,'reader_parts':parts,
                'serialized_source_parts':legacy.serialized_source_parts,'json_bytes':importer.json_bytes})
            output=scope['reader_payloads']
            self.assertGreaterEqual(len(output),len(parts))
            self.assertEqual(new.decode_source_parts(output[legacy.BASE],output.__getitem__,list(output)[1:]),value)
            if len(parts)==1:self.assertEqual(output[legacy.BASE],importer.json_bytes(value))

    def test_actual_importer_base_contract_requires_all_secondary_pins(self):
        tree=ast.parse((REPO/'tools/package-importer/importer.py').read_text(encoding='utf8'))
        loops=[node for node in ast.walk(tree) if isinstance(node,ast.For)
               and isinstance(node.iter,ast.Subscript) and isinstance(node.iter.value,ast.Name)
               and node.iter.value.id=='reader_parts']
        self.assertEqual(len(loops),2)
        contract_loop=next(node for node in loops if any(isinstance(child,ast.If) for child in node.body))
        replacement_loop=next(node for node in loops if node is not contract_loop)
        with tempfile.TemporaryDirectory() as tmp:
            checkout=Path(tmp);path=checkout/'recipe-atlas/data'/legacy.BASE
            legacy.write_reviewed_reader(path,sample());parts=legacy.source_paths(path)
            expected={p.relative_to(checkout).as_posix():'pinned' for p in parts}
            scope={'reader_parts':parts,'checkout':checkout,'expected_base':expected,
                   'base_paths':{},'base_replacements':{},'ImportRejected':importer.ImportRejected}
            execute([contract_loop,replacement_loop],scope)
            self.assertEqual(set(scope['base_paths']),set(expected)-{path.relative_to(checkout).as_posix()})
            self.assertEqual(set(scope['base_replacements']),set(scope['base_paths']))
            del expected[parts[-1].relative_to(checkout).as_posix()]
            with self.assertRaises(importer.ImportRejected):execute([contract_loop],scope)

    def test_actual_preflight_collects_all_parts_and_pins_the_new_adapter(self):
        tree=ast.parse((REPO/'tools/package-importer/preflight.py').read_text(encoding='utf8'))
        run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
        loop=next(n for n in run.body if isinstance(n,ast.For) and isinstance(n.iter,ast.Call)
                  and isinstance(n.iter.func,ast.Name) and n.iter.func.id=='source_paths')
        code_loop=next(n for n in run.body if isinstance(n,ast.For) and isinstance(n.iter,ast.Tuple)
                       and any(isinstance(v,ast.Constant) and v.value=='reader_presentation_registry.py' for v in n.iter.elts))
        self.assertIn('reader_source_multipart.py',[v.value for v in code_loop.iter.elts])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data'/legacy.BASE;legacy.write_reviewed_reader(path,sample())
            checked=[]
            execute([loop],{'reader_path':path,'source_paths':legacy.source_paths,
                           'checked':lambda p:checked.append((p.name,hashlib.sha256(p.read_bytes()).hexdigest()))})
            self.assertEqual([name for name,digest in checked],[p.name for p in legacy.source_paths(path)])

    def test_source_multipart_to_unchanged_public_and_browser_loader(self):
        value=sample();parts=legacy.serialized_source_parts(value,True)
        self.assertGreater(len(parts),2)
        logical=new.decode_source_parts(parts[legacy.BASE],parts.__getitem__,list(parts)[1:])
        with patch.object(public,'MAX_PART_BYTES',4096):output=public.public_parts(logical)
        self.assertEqual(public.load_public_parts(output[public.BASE],output.__getitem__),value)
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
        payload={'parts':{k:base64.b64encode(v).decode() for k,v in output.items()},'expected':value}
        result=subprocess.run(['node','--input-type=module','-e',script,
            (REPO/'recipe-atlas/static/reader-presentation-loader.mjs').as_uri()],
            input=json.dumps(payload),text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
