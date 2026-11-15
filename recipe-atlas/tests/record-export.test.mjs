import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash, webcrypto} from 'node:crypto';
import {collectRecordExport} from '../static/record-export.mjs';

const digest = raw => createHash('sha256').update(raw).digest('hex');
function fixture() {
  const chunks = [Buffer.from('{"record_id":"a","note":"α"}\n'), Buffer.from('{"record_id":"b"}\n')];
  const manifest = {schema: 'nanoxtalsyn-record-export/1', download_name: 'records.jsonl', encoding: 'utf-8',
    record_count: 2, bytes: Buffer.concat(chunks).length, sha256: digest(Buffer.concat(chunks)),
    parts: chunks.map((raw, i) => ({path: `records.part000${i + 1}.jsonl`, bytes: raw.length, record_count: 1, sha256: digest(raw)}))};
  const calls = [];
  const bodies = new Map(manifest.parts.map((p, i) => [p.path, chunks[i]]));
  const fetcher = async url => {
    calls.push(url);
    const name = new URL(url).pathname.split('/').at(-1);
    return name === 'records-manifest.json' ? {ok: true, json: async () => manifest} : new Response(bodies.get(name) ?? '', {status: bodies.has(name) ? 200 : 404});
  };
  const run = () => collectRecordExport('https://example.invalid/site/data/records-manifest.json', {fetcher, cryptoImpl: webcrypto});
  return {manifest, chunks, calls, bodies, run};
}

test('download reproduces all UTF-8 JSONL bytes in canonical order', async () => {
  const f = fixture(); const result = await f.run();
  assert.deepEqual(Buffer.from(await result.blob.arrayBuffer()), Buffer.concat(f.chunks));
  assert.equal(result.recordCount, 2); assert.equal(result.filename, 'records.jsonl');
  assert.equal(f.calls.length, 3);
  assert.ok(f.calls.every(url => url.startsWith('https://example.invalid/site/data/')));
});
test('out-of-order, unsafe, duplicate and unknown manifests fail before part fetching', async () => {
  for (const mutate of [f => f.manifest.parts.reverse(), f => { f.manifest.parts[0].path = '../other'; },
    f => f.manifest.parts.push(f.manifest.parts[0]), f => { f.manifest.schema = 'other'; },
    f => { f.manifest.parts[0].bytes = 81 * 1024 * 1024; }, f => { f.manifest.bytes++; }]) {
    const f = fixture(); mutate(f); await assert.rejects(f.run); assert.equal(f.calls.length, 1);
  }
});
test('missing, truncated and altered parts never produce a download', async () => {
  for (const mutate of [f => f.bodies.delete(f.manifest.parts[0].path),
    f => f.bodies.set(f.manifest.parts[0].path, f.chunks[0].subarray(1)),
    f => f.bodies.set(f.manifest.parts[0].path, Buffer.alloc(f.chunks[0].length))]) {
    const f = fixture(); mutate(f); await assert.rejects(f.run);
  }
});
test('wrong aggregate SHA and wrong line counts fail', async () => {
  const f = fixture(); f.manifest.sha256 = '0'.repeat(64); await assert.rejects(f.run, /Complete record export checksum/);
  const g = fixture(); g.manifest.parts[0].record_count = 2; g.manifest.record_count = 3;
  await assert.rejects(g.run, /part count disagrees/);
});
test('single legacy-named part still verifies', async () => {
  const f = fixture(); const raw = Buffer.concat(f.chunks);
  f.manifest.parts = [{path: 'records.jsonl', bytes: raw.length, record_count: 2, sha256: digest(raw)}];
  f.bodies.set('records.jsonl', raw); assert.equal((await f.run()).blob.size, raw.length);
});
