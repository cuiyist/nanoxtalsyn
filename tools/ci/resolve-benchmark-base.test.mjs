import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {checkReconciledDefaults,checkReconciledExplicitPins,resolveBaseTargets} from './resolve-benchmark-base.mjs';

const base='95df7dcb18150ee633e081d05c3d50babfe81c25';
const read=(commit,path)=>execFileSync('git',['show',commit+':'+path],{maxBuffer:4_000_000});
const config=()=>JSON.parse(fs.readFileSync('tools/ci/benchmark-base-reconciliations.json'));
const original=()=>JSON.parse(read(base,'tools/ci/protocol-scenes-targets.json'));
const replacement=()=>JSON.parse(fs.readFileSync('tools/ci/release06-before-protocol-targets.json'));

test('two stale defaults reconcile without changing any explicit regression target',()=>{
  checkReconciledDefaults(original(),replacement(),['default-cds','default-inp']);
});
test('reconciliation cannot change a route, formula, explicit regression or undeclared default',()=>{
  for(const change of ['route','formula','explicit','omitted','extra','operation']) {
    const r=replacement(),declared=['default-cds','default-inp'];
    if(change==='route')r.targets[1].route='material.html?id=wrong';
    if(change==='formula')r.targets[1].formula='wrong';
    if(change==='explicit')r.targets[10].operation_label+=' changed';
    if(change==='omitted')declared.pop();
    if(change==='extra')declared.push('default-au');
    if(change==='operation')r.targets[1].operation_index=1;
    assert.throws(()=>checkReconciledDefaults(original(),r,declared),change);
  }
});
test('fixed baseline resolves20 protocol and6 method targets with all Source byte pins',()=>{
  const r=resolveBaseTargets(base,read,fs.readFileSync,config());
  assert(r.reconciliation_used);assert.equal(r.protocol.targets.length,20);
  assert.equal(r.methods.targets.length,6);assert.equal(r.methods.phase,'before');
});
test('bad original, replacement, path or record pins fail instead of falling back',()=>{
  for(const change of ['original','replacement','path','record']) {
    const c=config(),entry=c.bases[base];
    if(change==='original')entry.original_protocol_sha256='0'.repeat(64);
    if(change==='replacement')entry.methods_sha256='0'.repeat(64);
    if(change==='path')entry.protocol_path='../outside.json';
    const source=(commit,path)=>change==='record'&&path.startsWith('recipe-atlas/data/records/')?Buffer.from('{}'):read(commit,path);
    assert.throws(()=>resolveBaseTargets(base,source,fs.readFileSync,c),change);
  }
});
test('an unlisted base keeps ordinary fixed snapshots and still checks every raw record',()=>{
  const c={schema:'fixed-benchmark-base-reconciliation/1',bases:{}};
  const r=resolveBaseTargets(base,read,fs.readFileSync,c);
  assert.equal(r.reconciliation_used,false);assert.equal(r.protocol.targets[1].record_id,original().targets[1].record_id);
});

const f6='9bf8126f2431047cd91de8d7f1d970ced9560294';
const f6Pins=()=>JSON.parse(fs.readFileSync('tools/ci/release12-before-protocol-targets.json'));
test('verified F6 refresh keeps 20 protocol and six method targets and follows the same injection',()=>{
  const r=resolveBaseTargets(f6,read,fs.readFileSync,config());
  assert(r.reconciliation_used);
  assert.equal(r.protocol.targets.length,20);
  assert.equal(r.methods.targets.length,6);
  const old=JSON.parse(read(f6,'tools/ci/protocol-scenes-targets.json')).targets.find(r=>r.id==='hot-injection');
  const next=r.protocol.targets.find(r=>r.id===old.id);
  for(const field of ['route','record_id','operation_id','operation_label','minimum_label_px_after'])assert.equal(next[field],old[field]);
  assert.equal(old.operation_index,1);
  assert.equal(next.operation_index,2);
});
test('verified F6 rebinding still denies even a declared identity change and requires every change',()=>{
  const metadata=config().bases[f6],start=JSON.parse(read(f6,'tools/ci/protocol-scenes-targets.json'));
  for(const change of ['label','record','route','omitted','extra']){
    const candidate=f6Pins(),target=candidate.targets.find(r=>r.id==='hot-injection');
    const declared=[...metadata.changed_protocol_explicit];
    if(change==='label')target.operation_label+=' replacement';
    if(change==='record'){
      target.route=target.route.replace(target.record_id,'not-the-target');
      target.record_id='not-the-target';
    }
    if(change==='route')target.route='cdse.html?method='+target.record_id;
    if(change==='omitted')declared.pop();
    if(change==='extra')declared.push('default-zns');
    assert.throws(()=>checkReconciledExplicitPins(start,candidate,metadata.changed_protocol_defaults,declared),change);
  }
  const wrongRead=(commit,file)=>file.includes('/records/li2010-ie901086d')?Buffer.from('{}'):read(commit,file);
  assert.throws(()=>resolveBaseTargets(f6,wrongRead,fs.readFileSync,config()));
});
