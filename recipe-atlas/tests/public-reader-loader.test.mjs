import {readFileSync} from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {createReaderPresentationLoader} from '../static/reader-presentation-loader.mjs';
const BASE='https://example.test/data/reader-presentation.json';
const PART='https://example.test/data/reader-presentation.part2.json';
const encode=v=>new TextEncoder().encode(JSON.stringify(v));
const sha=async raw=>Buffer.from(await webcrypto.subtle.digest('SHA-256',raw)).toString('hex');
const logical=()=>({records:{r:{status:'source_extracted',training_eligible:false,figures:[{caption:'short paraphrase',origin:'manual',cropSHA:'a'.repeat(64)}]}},materials:{m:{record_ids:['r'],component_only:true}},figures_by_source:{s:[]},counter:9});
async function split(){const v=logical();const part={records:v.records,materials:{},figures_by_source:{s:[]}};const raw=encode(part);return {base:{...v,records:{},figures_by_source:{},_reader_registry_split:{schema:'reader-presentation-two-part/1',part:'reader-presentation.part2.json',sha256:await sha(raw)}},part,raw,v};}
function fixture(entries){const calls=[];const load=createReaderPresentationLoader({crypto:webcrypto,fetcher:async(url,opt)=>{calls.push([url,opt]);const raw=entries.get(url);return {ok:raw!==undefined,arrayBuffer:async()=>Uint8Array.from(raw).buffer};}});return {load,calls};}
test('current monolith preserves full logical data and one shared request',async()=>{const v=logical();const {load,calls}=fixture(new Map([[BASE,encode(v)]]));const [a,b]=await Promise.all([load(BASE),load(new URL(BASE))]);assert.strictEqual(a,b);assert.deepEqual(a,v);assert.equal(calls.length,1);assert.equal(calls[0][1].cache,'no-store');});
test('checksum verified split has exact same full data and shared cache',async()=>{const s=await split();const {load,calls}=fixture(new Map([[BASE,encode(s.base)],[PART,s.raw]]));const [a,b]=await Promise.all([load(BASE),load(new URL(BASE))]);assert.strictEqual(a,b);assert.deepEqual(a,s.v);assert.equal(calls.length,2);assert.ok(!('_reader_registry_split'in a));});
test('checksum mismatch rejects without fallback or repeated request',async()=>{const s=await split();s.base._reader_registry_split.sha256='0'.repeat(64);const {load,calls}=fixture(new Map([[BASE,encode(s.base)],[PART,s.raw]]));await assert.rejects(load(BASE),/checksum/);await assert.rejects(load(BASE),/checksum/);assert.equal(calls.length,2);});
test('missing secondary rejects',async()=>{const s=await split();const {load}=fixture(new Map([[BASE,encode(s.base)]]));await assert.rejects(load(BASE),/Unavailable/);});
for(const table of ['records','materials','figures_by_source'])test('duplicate '+table+' key rejects',async()=>{const s=await split();const key=Object.keys(s.v[table])[0];s.base[table]={[key]:s.v[table][key]};s.part[table]={[key]:s.v[table][key]};s.raw=encode(s.part);s.base._reader_registry_split.sha256=await sha(s.raw);const {load}=fixture(new Map([[BASE,encode(s.base)],[PART,s.raw]]));await assert.rejects(load(BASE),/Duplicate/);});
test('secondary extra fields reject',async()=>{const s=await split();s.part.extra=true;s.raw=encode(s.part);s.base._reader_registry_split.sha256=await sha(s.raw);const {load}=fixture(new Map([[BASE,encode(s.base)],[PART,s.raw]]));await assert.rejects(load(BASE),/Unexpected/);});
test('invalid marker shape/schema/path/hash fail before secondary fetch',async()=>{for(const change of [m=>m.part='../private.json',m=>m.schema='wrong',m=>m.sha256='bad',m=>m.extra=1]){const s=await split();change(s.base._reader_registry_split);const {load,calls}=fixture(new Map([[BASE,encode(s.base)],[PART,s.raw]]));await assert.rejects(load(BASE),/marker/);assert.equal(calls.length,1);}});
test('null marker and nonobject primary table reject',async()=>{for(const v of [{...logical(),_reader_registry_split:null},{...logical(),records:[]}]){const {load}=fixture(new Map([[BASE,encode(v)]]));await assert.rejects(load(BASE));}});
test('UTF8/JSON malformed input rejects',async()=>{for(const raw of [Uint8Array.of(255),new TextEncoder().encode('{')]){const {load}=fixture(new Map([[BASE,raw]]));await assert.rejects(load(BASE));}});
test('no checksum API rejects split but current monolith still loads',async()=>{const s=await split();const entries=new Map([[BASE,encode(s.base)],[PART,s.raw]]);const load=createReaderPresentationLoader({crypto:null,fetcher:async url=>({ok:true,arrayBuffer:async()=>entries.get(url).buffer})});await assert.rejects(load(BASE),/verification unavailable/);});
test('arbitrary base filename rejects without fetch',async()=>{const {load,calls}=fixture(new Map());await assert.rejects(load('https://example.test/data/private.json'),/fixed/);assert.equal(calls.length,0);});
test('normal Python builder fixture loads with exact logical/display parity',async()=>{const read=name=>new Uint8Array(readFileSync(new URL('./fixtures/public-reader-split/'+name,import.meta.url)));const expected=JSON.parse(new TextDecoder().decode(read('expected-logical.json')));const {load}=fixture(new Map([[BASE,read('reader-presentation.json')],[PART,read('reader-presentation.part2.json')]]));assert.deepEqual(await load(BASE),expected);assert.equal(expected.records.r0.figures[0].display_kind,'source_link');assert.equal(expected.records.r0.figures[0].origin,'manual');assert.equal(expected.records.r0.training_eligible,false);});
async function multipart(){
 const v=logical(),parts=[{records:v.records,materials:{},figures_by_source:{}},{records:{},materials:v.materials,figures_by_source:{}},{records:{},materials:{},figures_by_source:v.figures_by_source}];
 const refs=[],entries=new Map();
 for(const [i,part]of parts.entries()){const name=`reader-presentation.part${i+2}.json`,raw=encode(part);refs.push({part:name,sha256:await sha(raw)});entries.set(new URL(name,BASE).href,raw);}
 const base={...v,records:{},materials:{},figures_by_source:{},_reader_registry_split:{schema:'reader-presentation-parts/1',parts:refs}};
 entries.set(BASE,encode(base));return {v,base,parts,refs,entries};
}
test('three verified data parts load complete data once, preserving status and figures',async()=>{const s=await multipart();const {load,calls}=fixture(s.entries);const [a,b]=await Promise.all([load(BASE),load(BASE)]);assert.strictEqual(a,b);assert.deepEqual(a,s.v);assert.equal(calls.length,4);});
test('all multipart names and hashes validate before any secondary fetch',async()=>{
 for(const change of [m=>m.parts=[],m=>m.parts.push(m.parts[0]),m=>m.parts[2].part='../private.json',m=>m.parts[2].sha256='bad',m=>m.parts[2].extra=1,m=>m.extra=1,m=>m.parts=Array(1025).fill(m.parts[0])]){
  const s=await multipart();change(s.base._reader_registry_split);s.entries.set(BASE,encode(s.base));const {load,calls}=fixture(s.entries);await assert.rejects(load(BASE),/marker/);assert.equal(calls.length,1);
 }
});
test('missing final part rejects the entire view and cached retries do not refetch',async()=>{const s=await multipart();s.entries.delete(new URL(s.refs[2].part,BASE).href);const {load,calls}=fixture(s.entries);await assert.rejects(load(BASE),/Unavailable/);await assert.rejects(load(BASE),/Unavailable/);assert.equal(calls.length,4);});
test('corrupt final part rejects the entire view',async()=>{const s=await multipart();s.entries.set(new URL(s.refs[2].part,BASE).href,encode({}));const {load}=fixture(s.entries);await assert.rejects(load(BASE),/checksum/);});
test('duplicate keys between secondary parts reject',async()=>{const s=await multipart();s.parts[2].records=s.v.records;const raw=encode(s.parts[2]);s.refs[2].sha256=await sha(raw);s.entries.set(new URL(s.refs[2].part,BASE).href,raw);s.entries.set(BASE,encode(s.base));const {load}=fixture(s.entries);await assert.rejects(load(BASE),/Duplicate/);});
