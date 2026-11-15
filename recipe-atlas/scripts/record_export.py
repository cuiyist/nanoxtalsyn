"""Lossless, deterministic whole-record JSONL transport with bounded Git blobs."""
import hashlib
import json
from pathlib import Path
import re

SCHEMA = 'nanoxtalsyn-record-export/1'
MANIFEST = 'records-manifest.json'
MAX_PART_BYTES = 80 * 1024 * 1024
PART = re.compile(r'records\.part[0-9]{4,}\.jsonl')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode_record(record):
    return (json.dumps(record, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def plan_export(records, max_part_bytes=MAX_PART_BYTES):
    """Forecast every serialized byte before writing; never split a record."""
    require(type(max_part_bytes) is int and 0 < max_part_bytes <= MAX_PART_BYTES, 'Invalid record part limit')
    chunks, counts, current, count, seen = [], [], bytearray(), 0, set()
    whole = hashlib.sha256()
    for record in records:
        rid = record.get('record_id')
        require(isinstance(rid, str) and rid and rid not in seen, 'Missing or duplicate record ID')
        seen.add(rid)
        raw = encode_record(record)
        require(len(raw) <= max_part_bytes, 'One record exceeds the JSONL part limit')
        if current and len(current) + len(raw) > max_part_bytes:
            chunks.append(bytes(current)); counts.append(count)
            current, count = bytearray(), 0
        current.extend(raw); count += 1; whole.update(raw)
    if current or not chunks:
        chunks.append(bytes(current)); counts.append(count)
    names = ['records.jsonl'] if len(chunks) == 1 else [f'records.part{i:04d}.jsonl' for i in range(1, len(chunks) + 1)]
    files = dict(zip(names, chunks))
    manifest = {'schema': SCHEMA, 'download_name': 'records.jsonl', 'encoding': 'utf-8',
                'record_count': len(seen), 'bytes': sum(map(len, chunks)), 'sha256': whole.hexdigest(),
                'parts': [{'path': name, 'bytes': len(raw), 'record_count': n, 'sha256': sha(raw)}
                          for name, raw, n in zip(names, chunks, counts)]}
    files[MANIFEST] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    require(len(files[MANIFEST]) <= MAX_PART_BYTES, 'Record export manifest exceeds the part limit')
    return manifest, files


def write_export(data, records, max_part_bytes=MAX_PART_BYTES):
    data = Path(data)
    manifest, files = plan_export(records, max_part_bytes)
    existing = {p.name for p in data.iterdir() if p.name == 'records.jsonl' or PART.fullmatch(p.name)}
    require(not existing - files.keys(), 'Stale record export transport; use the normal clean build')
    for name, raw in files.items():
        path = data / name
        require(not path.is_symlink(), 'Symlink record export target')
        path.write_bytes(raw)
        require(path.stat().st_size == len(raw) and sha(path.read_bytes()) == sha(raw), 'Written record export differs')
    return manifest


def read_export(data):
    """Validate a full ordered export before returning any records; support old sites."""
    data = Path(data)
    path = data / MANIFEST
    if not path.exists():
        require(not any(PART.fullmatch(p.name) for p in data.iterdir()), 'Sharded export lacks its manifest')
        return [json.loads(line) for line in (data / 'records.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    require(not path.is_symlink() and path.stat().st_size <= MAX_PART_BYTES, 'Unsafe record manifest')
    manifest = json.loads(path.read_bytes())
    require(manifest.get('schema') == SCHEMA and manifest.get('download_name') == 'records.jsonl'
            and manifest.get('encoding') == 'utf-8', 'Unknown record export contract')
    parts = manifest.get('parts')
    require(isinstance(parts, list) and parts, 'Record export parts missing')
    names = ['records.jsonl'] if len(parts) == 1 and parts[0].get('path') == 'records.jsonl' else [f'records.part{i:04d}.jsonl' for i in range(1, len(parts) + 1)]
    require([p.get('path') for p in parts] == names, 'Record parts are not in canonical order')
    actual = {p.name for p in data.iterdir() if p.name == 'records.jsonl' or PART.fullmatch(p.name)}
    require(actual == set(names), 'Missing or stale record export transport')
    records, seen, whole, total = [], set(), hashlib.sha256(), 0
    for part in parts:
        leaf = data / part['path']
        require(type(part.get('bytes')) is int and 0 <= part['bytes'] <= MAX_PART_BYTES,
                'Invalid record part byte count')
        require(leaf.is_file() and not leaf.is_symlink() and leaf.stat().st_size == part['bytes'], 'Record part size differs')
        raw = leaf.read_bytes()
        require(sha(raw) == part.get('sha256'), 'Record part SHA differs')
        require(not raw or raw.endswith(b'\n'), 'Truncated record part')
        rows = [json.loads(line) for line in raw.decode('utf-8').splitlines()]
        require(type(part.get('record_count')) is int and len(rows) == part['record_count'], 'Record part count differs')
        for row in rows:
            rid = row.get('record_id')
            require(isinstance(rid, str) and rid and rid not in seen, 'Missing or duplicate record ID')
            seen.add(rid)
        records.extend(rows); total += len(raw); whole.update(raw)
    require(type(manifest.get('record_count')) is int and len(records) == manifest['record_count'], 'Aggregate record count differs')
    require(type(manifest.get('bytes')) is int and total == manifest['bytes'] and whole.hexdigest() == manifest.get('sha256'), 'Aggregate record bytes/SHA differ')
    return records
