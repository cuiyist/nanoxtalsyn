import test from 'node:test';
import assert from 'node:assert/strict';
import {methodPicker} from '../static/compact-method-state.mjs';

function fixture(){
  const groups={families:Array.from({length:5},(_,f)=>({id:'f'+f,label:f===4?'CdSe as shell or component':'Hot injection '+f,
    nonmetal_source:f===3?'Elemental selenium':undefined,paper_count:3,papers:Array.from({length:3},(_,p)=>({
      citation:p===2?'Muñoz (2003)':'Ames (2000)',record_ids:p===1?[`${f}p${p}`,`${f}p${p}-v2`]:[`${f}p${p}`],
    }))}))};
  const records=groups.families.flatMap(g=>g.papers.flatMap(p=>p.record_ids.map(rid=>({record_id:rid,
    method_source_names:rid==='3p2'?['cadmium acetate']:[],year:rid.endsWith('p2')?2003:2000}))));
  return {groups,records};
}

test('deep link adds only the selected card under its own family',()=>{
  const {groups,records}=fixture(),api=methodPicker(groups,records);
  const before=structuredClone(groups);
  const view=api.preview('4p1-v2');
  assert.deepEqual(view.map(x=>x.cards.length),[2,2,2,1]);
  assert.equal(view.at(-1).family.id,'f4');assert.deepEqual(view.at(-1).cards[0].record_ids,['4p1','4p1-v2']);
  assert.deepEqual(api.preview('0p1').map(x=>x.cards.length),[2,2,2]);
  assert.deepEqual(groups,before);
});

test('filter matches diacritic-normalized citation and chemical names and year',()=>{
  const {groups,records}=fixture(),api=methodPicker(groups,records);
  const filtered=api.filter('munoz 2003 selenium cadmium acetate');
  assert.equal(filtered.length,1);assert.deepEqual(filtered[0].cards[0].record_ids,['3p2']);
  assert.equal(api.filter('CdSe as shell or component')[0].family.id,'f4');
  assert.equal(api.filter('nonmatching').length,0);
});

test('prev and next stay within the selected family, including variants',()=>{
  const {groups,records}=fixture(),api=methodPicker(groups,records);
  assert.deepEqual(api.selected('3p1'),{citation:'Ames (2000)',family:'Hot injection 3',previous:'3p0',next:'3p1-v2'});
  assert.equal(api.selected('3p0').previous,null);assert.equal(api.selected('3p2').next,null);
});
