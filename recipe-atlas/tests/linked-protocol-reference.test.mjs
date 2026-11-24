import test from 'node:test';
import assert from 'node:assert/strict';
import {sceneState} from '../static/linked-vessel-state.mjs';
import {overlayVesselState} from '../static/linked-vessel-drawing.mjs';
import {closedCrystalCell,smallMoleculeThumbnailScale} from '../static/closed-cell-geometry.mjs';

const reported=value=>({status:'reported',value});
function scene(){return {materials:[{id:'new',name:'Synthetic feed'}],material_states:[{id:'m1',kind:'reaction_batch'},{id:'m2',kind:'reaction_batch'}],operations:[
 {id:'heat',action:'heat',parameters:{temperature:reported(300)},environment:reported('N2'),outputs:['m1']},
 {id:'wait',action:'hold',depends_on:['heat'],inputs:['m1'],outputs:['m2']},
 {id:'add',action:'inject',depends_on:['wait'],inputs:['new','m2'],parameters:{}}
]};}

test('only linked mixture inherits, numbers stay off the current step cards',()=>{
  const r=scene();const out=sceneState(r,2);
  assert.equal(out.carry.temperature.label,'from step 1');assert.equal(out.carry.atmosphere.quantity.value,'N2');
  assert.equal(out.inletLabel,'Synthetic feed');assert.equal(out.ownTemperatureReported,false);
  assert.deepEqual(r.operations[2].parameters,{});
  r.operations[2].inputs=['new'];assert.deepEqual(sceneState(r,2).carry,{});
});
test('an intervening cooling or purge blocks only the affected state',()=>{
 const r=scene();r.operations[1].action='cool';
 assert.equal(sceneState(r,2).carry.temperature,undefined);assert.equal(sceneState(r,2).carry.atmosphere.label,'from step 1');
 r.operations[1].action='purge';assert.equal(sceneState(r,2).carry.atmosphere,undefined);assert.equal(sceneState(r,2).carry.temperature.label,'from step 1');
});

test('drawing labels a syringe without assuming an unreported feed',()=>{
  const r=scene(),spec={kind:'inject',added:[],addedLabels:[],addedFormulas:[]};
  const step=r.operations[2],earlier=()=>({kind:'solution',heating:true,gasLine:true});
  const draw=(value)=>overlayVesselState(value,r,step,earlier,q=>String(q.value));
  assert.equal(draw(spec).syringeInput,'Synthetic feed');
  step.inputs=['m2'];
  assert.deepEqual(draw(spec).added,[]);
  assert.equal(draw(spec).syringeInputUnstated,true);
  assert.equal(draw({...spec,added:['First stated feed','Second stated feed']}).syringeInput,'First stated feed + Second stated feed');
  assert.deepEqual(spec.added,[]);
  assert.deepEqual(step.parameters,{});
});

test('closed rocksalt shows cube corners, face and edge sites, and reciprocal nearest links',()=>{
 const atoms=[];
 for(let x=0;x<2;x++)for(let y=0;y<2;y++)for(let z=0;z<2;z++)atoms.push({x,y,z,element:(x+y+z)%2?'Y':'X'});
 const model={cellVectors:[[2,0,0],[0,2,0],[0,0,2]],atoms};
 const cell=closedCrystalCell(model);
 assert.equal(atoms.length,8);assert.equal(cell.originalAtomCount,8);assert.equal(cell.atoms.length,27);
 assert.equal(cell.nearestReferenceDistance,1);assert.equal(cell.bonds.length,54);
 const corners=cell.atoms.filter(a=>[a.x,a.y,a.z].every(v=>v===0||v===2));assert.equal(corners.length,8);
 for(const [a,b] of cell.bonds){assert.notEqual(cell.atoms[a].elem,cell.atoms[b].elem);assert(cell.atoms[b].bonds.includes(a));}
});
test('small molecule card caps bond length rather than stretching to fit',()=>{
 assert.equal(smallMoleculeThumbnailScale([[-1,0,0],[1,0,0]],[[1,0,0],[0,1,0]],[[0,1]],180,100,44),22);
});
