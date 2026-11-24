import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import test from 'node:test';
import {assembleCellView} from '../static/closed-cell-display.mjs';

const base=new URL('../static/assets/crystal-references/models/',import.meta.url);
for(const [formula,file,atomCount,bounds] of [
  ['CdO','cdo-rocksalt-cod-9006671.json',27,54],
  ['NaCl','nacl-rocksalt-cod-9003308.json',27,54],
  // Four interior As sites each connect to four FCC In sites in the cell.
  ['InAs','inas-zinc-blende-cod-9008851.json',18,16],
])test(`closed ${formula} reference cell shows neighbours without modifying model`,async()=>{
  const model=JSON.parse(await readFile(new URL(file,base),'utf8'));
  const original=JSON.stringify(model),a=model.cell.a,b=model.cell.b,c=model.cell.c;
  assert.equal(model.cell.alpha,90);assert.equal(model.cell.beta,90);assert.equal(model.cell.gamma,90);
  const display=assembleCellView(model,[[a,0,0],[0,b,0],[0,0,c]]);
  assert.equal(display.originalAtomCount,8);
  assert.equal(display.atoms.length,atomCount);assert.equal(display.bonds.length,bounds);
  const degree=display.atoms.map(a=>a.bonds.length);
  assert.equal(Math.max(...degree),formula==='InAs'?4:6);
  assert.equal(JSON.stringify(model),original);
});

for(const file of ['ch3nh3pbbr3-cubic-perovskite-cod-1545320.json','fapbbr3-cubic-perovskite-cod-1545319.json']){
  test(`dense ${file} keeps the existing repeated view and occupancy markings`,async()=>{
    const model=JSON.parse(await readFile(new URL(file,base),'utf8'));
    const original=JSON.stringify(model),{a,b,c}=model.cell;
    const display=assembleCellView(model,[[a,0,0],[0,b,0],[0,0,c]],2);
    assert.equal(display.atoms.length,3116);
    assert.equal(display.atoms.filter(atom=>atom.mixed_site||(atom.properties.display_occupancy??-1)<1).length,3072);
    assert(display.atoms.some(atom=>atom.boundaryReplica));
    assert(display.bonds.every(([i,j])=>[i,j].every(k=>!display.atoms[k].mixed_site&&display.atoms[k].properties.display_occupancy===1)));
    assert.equal(JSON.stringify(model),original);
  });
}
