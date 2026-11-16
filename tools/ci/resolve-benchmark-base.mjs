// Resolve fixed, source-byte-bound BEFORE targets. Never adapt to browser results.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import {validateTargets, beforeTargetsFromBaseSnapshot, K_REGRESSION_TARGETS} from './protocol-scenes-check.mjs';
import {beforeTargetsFromProtocolSnapshot} from './method-families-check.mjs';

const sha = raw => createHash('sha256').update(raw).digest('hex');
const PROTOCOL = 'tools/ci/protocol-scenes-targets.json';
const METHODS = 'tools/ci/method-families-targets.json';
const changedFields = new Set(['record_id','operation_index','operation_id','operation_label','record_json_bytes','record_json_sha256']);

export function checkReconciledDefaults(original, replacement, declared) {
  validateTargets(original); validateTargets(replacement);
  assert.equal(original.schema, replacement.schema);
  assert.equal(original.targets.length, replacement.targets.length);
  assert(Array.isArray(declared) && new Set(declared).size === declared.length);
  const changed = [];
  for (let i=0; i<original.targets.length; i++) {
    const old=original.targets[i], next=replacement.targets[i];
    assert.equal(old.id, next.id);
    if (JSON.stringify(old) === JSON.stringify(next)) continue;
    assert.equal(old.group, 'benchmark-default', 'Explicit regression targets cannot be reconciled');
    assert.equal(next.operation_index, 0, 'Actual default first operation required');
    for (const key of new Set([...Object.keys(old),...Object.keys(next)])) {
      if (!changedFields.has(key)) assert.deepEqual(next[key], old[key], 'Default route/formula/group cannot change');
    }
    changed.push(old.id);
  }
  assert.deepEqual(changed.sort(), [...declared].sort(), 'Every and only declared default change is required');
}

export function resolveBaseTargets(base, readGit, readFile, reconciliations) {
  assert(/^[0-9a-f]{40}$/.test(base), 'Exact comparison-base commit required');
  assert.equal(reconciliations.schema, 'fixed-benchmark-base-reconciliation/1');
  const originalProtocol=readGit(base,PROTOCOL), originalMethods=readGit(base,METHODS);
  let protocol=JSON.parse(originalProtocol), methods=JSON.parse(originalMethods);
  const entry=reconciliations.bases[base];
  if (entry) {
    assert.equal(entry.original_protocol_sha256,sha(originalProtocol));
    assert.equal(entry.original_methods_sha256,sha(originalMethods));
    assert(/^[0-9a-f]{40}$/.test(entry.prior_site_commit));
    for (const kind of ['protocol','methods']) {
      assert(new RegExp('^tools/ci/release[0-9]+-before-'+(kind==='protocol'?'protocol':'method')+'-targets\\.json$').test(entry[kind+'_path']));
    }
    const pr=readFile(entry.protocol_path), mr=readFile(entry.methods_path);
    assert.equal(sha(pr),entry.protocol_sha256);
    assert.equal(sha(mr),entry.methods_sha256);
    const revisedProtocol=JSON.parse(pr), revisedMethods=JSON.parse(mr);
    checkReconciledDefaults(protocol,revisedProtocol,entry.changed_protocol_defaults);
    assert.equal(methods.schema,revisedMethods.schema);
    assert.equal(methods.phase,revisedMethods.phase);
    assert.equal(methods.preview_policy,revisedMethods.preview_policy);
    assert.deepEqual(methods.targets.map(r=>[r.id,r.formula,r.material_id,r.route]),
                     revisedMethods.targets.map(r=>[r.id,r.formula,r.material_id,r.route]));
    protocol=revisedProtocol; methods=revisedMethods;
  }
  validateTargets(protocol);
  // Check every exact record and operation against comparison-base Source, not
  // the later checkout or an anonymous page's claimed default.
  for (const target of protocol.targets) {
    const raw=readGit(base,'recipe-atlas/data/records/'+target.record_id+'.json');
    assert.equal(raw.length,target.record_json_bytes);
    assert.equal(sha(raw),target.record_json_sha256,'Comparison-base canonical record byte pin differs');
    const record=JSON.parse(raw), operation=record.operations[target.operation_index];
    assert.equal(record.record_id,target.record_id);
    assert.equal(operation.id,target.operation_id);
    assert.equal(operation.label,target.operation_label);
  }
  const k=Object.fromEntries(K_REGRESSION_TARGETS.map(t=>[t.record_id,readGit(base,'recipe-atlas/data/records/'+t.record_id+'.json')]));
  const before=beforeTargetsFromBaseSnapshot(protocol,k);
  return {protocol:before,methods:beforeTargetsFromProtocolSnapshot(before,methods),
          reconciliation_used:!!entry,comparison_base:base};
}

function main(argv) {
  assert.equal(argv.length,6);
  const opts={};for(let i=0;i<argv.length;i+=2){assert(['--base','--protocol-out','--methods-out'].includes(argv[i])&&!Object.hasOwn(opts,argv[i]));opts[argv[i]]=argv[i+1];}
  const base=opts['--base'];assert(/^[0-9a-f]{40}$/.test(base));
  const result=resolveBaseTargets(base,(commit,path)=>execFileSync('git',['show',commit+':'+path],{maxBuffer:4_000_000}),
    path=>fs.readFileSync(path),JSON.parse(fs.readFileSync('tools/ci/benchmark-base-reconciliations.json')));
  for (const [kind,option] of [['protocol','--protocol-out'],['methods','--methods-out']]) {
    fs.writeFileSync(opts[option],JSON.stringify(result[kind])+'\n',{flag:'wx'});
  }
  console.log(JSON.stringify({comparison_base:base,reconciliation_used:result.reconciliation_used,
    protocol_targets:result.protocol.targets.length,method_targets:result.methods.targets.length,
    all_comparison_base_record_pins_verified:true,browser_checks_unchanged:true}));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)main(process.argv.slice(2));
