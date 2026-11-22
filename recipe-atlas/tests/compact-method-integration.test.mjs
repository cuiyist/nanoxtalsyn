import assert from 'node:assert/strict';
import test from 'node:test';
import {completeChooserGroups,revealSelectedRecipe} from '../static/compact-method-chooser.mjs';
import {methodPicker} from '../static/compact-method-state.mjs';

test('standalone fallback uses the same compact rules without inventing any route',()=>{
  const records=Array.from({length:9},(_,i)=>({record_id:'r'+i,doi:i===2?'d1':'d'+i,title:'Title '+i,source_citation:'Author '+i,year:2000+i}));
  const groups=completeChooserGroups(null,records,'CdSe'),picker=methodPicker(groups,records);
  assert.equal(groups.default_record_id,'r0');
  assert.equal(groups.families[0].paper_count,8);
  assert.equal(picker.preview('r8')[0].cards.length,3);
  assert.deepEqual(picker.filter('2002')[0].cards[0].record_ids,['r1','r2']);
  assert.equal(picker.selected('r2').previous,'r1');
  assert.equal(picker.selected('r2').family,'Other methods');
  assert.equal(completeChooserGroups(groups,records,'CdSe'),groups);
});

test('only the completed selected record can take recipe focus',()=>{
  const calls=[],title={setAttribute(...args){calls.push(args);},focus(args){calls.push(args);}};
  const section={hidden:false,querySelector(){return title;},scrollIntoView(args){calls.push(args);}};
  const root={dataset:{readerReady:'current'},querySelector(){return section;}};
  assert.equal(revealSelectedRecipe(root,'stale'),false);assert.deepEqual(calls,[]);
  assert.equal(revealSelectedRecipe(root,'current'),true);
  assert.deepEqual(calls,[['tabindex','-1'],{preventScroll:true},{block:'start',behavior:'instant'}]);
});
