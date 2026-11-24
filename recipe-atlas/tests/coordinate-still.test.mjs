import assert from 'node:assert/strict';
import test from 'node:test';
import {thumbnailLayout,drawStillReference} from '../static/coordinate-still.mjs';
import {precursorReferencePicture} from '../static/coordinate-still-loader.mjs';

test('a nitrogen still uses actual geometry without stretching or text',()=>{
  const coords=[{x:0,y:0,z:-.56,element:'N'},{x:0,y:0,z:.56,element:'N'}];
  const layout=thumbnailLayout(coords,[[0,1]]);
  assert.equal(layout.atoms.length,2);
  const [a,b]=layout.atoms;assert.ok(Math.abs(Math.hypot(a.x-b.x,a.y-b.y)-48)<.002);
  const doc={createElementNS(ns,tag){return {tag,children:[],attrs:{},setAttribute(k,v){this.attrs[k]=v;},append(x){this.children.push(x);}};}};
  const svg=drawStillReference(doc,layout,'Nitrogen reference');
  assert.equal(svg.attrs['aria-label'],'Nitrogen reference');
  assert.deepEqual(svg.children.map(n=>n.tag).sort(),['circle','circle','line']);
});

test('a precursor card does not fall back to a text-only SVG',()=>{
  const doc={createElement(tag){return {tag,style:{},setAttribute(k,v){this[k]=v;},isConnected:false};}};
  const unneeded=()=>assert.fail('Text-only or temporarily blank cards must not fetch an old SVG');
  const flat=precursorReferencePicture(doc,{depictionKind:'formula'},{},unneeded);
  assert.equal(flat.tag,'p');assert.equal(flat.style.fontSize,'13px');
  assert.equal(flat.textContent,'No reference drawing is assigned.');
  const sha='a'.repeat(64),plain={depictionKind:'molecule',model2dPath:'models/example-2d.json',assetHashes:{model2dPath:sha}};
  assert.equal(precursorReferencePicture(doc,plain,{},()=>42),42);
  const pinned=precursorReferencePicture(doc,{...plain,model3dPath:'models/example-3d.json',assetHashes:{...plain.assetHashes,model3dPath:sha}},{},unneeded);
  assert.equal(pinned.tag,'div');assert.equal(pinned['aria-hidden'],'true');
  assert.equal(pinned.className,'chemical-preview chemical-coordinate-pending');
});
