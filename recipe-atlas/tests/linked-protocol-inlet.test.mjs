import test from 'node:test';
import assert from 'node:assert/strict';
import {compactDrawingFacts} from '../static/protocol-record-fit.mjs';

function compact(exact,{kind='inject',formula=null,syringeInput=exact}={}){
  const original={added:[{label:exact}],sources:[],durations:[],flowHeaterTemperatures:[],substrateLabels:[],atmosphere:''};
  const result=compactDrawingFacts(original,{kind,syringeInput,added:[exact],addedFormulas:[formula]},[],{fallback:true,minimalLabels:true});
  assert.equal(original.added[0].label,exact);
  return result;
}

test('a linked syringe uses a bounded name and retains the exact wording at its callout',()=>{
  const exact='Verified feed injection stock';
  const {facts,fullFacts}=compact(exact);
  assert.equal(facts.added[0].label,'Verified feed ↗');
  assert.equal(fullFacts[0].value,exact);
  assert.equal(fullFacts[0].callout,facts.added[0].label);
});
test('a short exact label needs no callout',()=>{
  const {facts,fullFacts}=compact('Verified feed');
  assert.equal(facts.added[0].label,'Verified feed');
  assert.deepEqual(fullFacts,[]);
});
test('long arbitrary terms are not truncated or fabricated',()=>{
  const exact='An explicitly reported and extensively named proprietary feed';
  assert.equal(compact(exact).facts.added[0].label,'Input 1 ↗');
  const {facts,fullFacts}=compact(exact,{formula:'NaCl'});
  assert.equal(facts.added[0].label,'NaCl ↗');
  assert.equal(fullFacts[0].value,exact);
  assert.equal(compact(exact,{kind:'mix',formula:'NaCl'}).facts.added[0].label,'Input 1 ↗');
});
test('equal short formulas in one syringe cannot point at the wrong exact input',()=>{
  const exact=['A specifically named first sodium chloride feed','A specifically named second sodium chloride feed'];
  const first=exact[0],second=exact[1];
  const original={added:exact.map(label=>({label})),sources:[],durations:[],flowHeaterTemperatures:[],substrateLabels:[],atmosphere:''};
  const {facts,fullFacts}=compactDrawingFacts(original,{kind:'inject',syringeInput:exact.join(' + '),
    added:exact,addedFormulas:['NaCl','NaCl']},[],{fallback:true,minimalLabels:true});
  assert.deepEqual(facts.added.map(x=>x.label),['Input 1 ↗','Input 2 ↗']);
  assert.deepEqual(fullFacts.map(x=>[x.callout,x.value]),[['Input 1 ↗',first],['Input 2 ↗',second]]);
});
