"""Bounded Source storage, separate from the legacy/public serializer contract.

Source parts contain opaque whole entries. The primary retains all non-table
metadata and pins sequential fixed-name data parts. No record is rewritten.
"""
import hashlib
import json
import os
from pathlib import Path
import re

import reader_presentation_registry as legacy

BASE=legacy.BASE
PART=legacy.PART
MARKER=legacy.MARKER
TABLES=legacy.TABLES
SCHEMA='reader-presentation-source-parts/1'
MAX_PARTS=1024


def _sha(raw):return hashlib.sha256(raw).hexdigest()


def _parse(raw):
    if not isinstance(raw,bytes) or len(raw)>legacy.MAX_PART_BYTES:
        raise ValueError('Reader source part exceeds the bounded byte limit')
    value=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(value,dict):raise ValueError('Reader source must be an object')
    return value


def part_refs(marker):
    if not isinstance(marker,dict):raise ValueError('Invalid Reader Source split marker')
    if set(marker)=={'schema','part','sha256'} and marker['schema']=='reader-presentation-two-part/1':
        refs=[{'part':marker['part'],'sha256':marker['sha256']}]
    elif set(marker)=={'schema','parts'} and marker['schema']==SCHEMA:
        refs=marker['parts']
    else:raise ValueError('Invalid Reader Source split marker')
    if not isinstance(refs,list) or not 1<=len(refs)<MAX_PARTS:
        raise ValueError('Invalid Reader Source part count')
    for ordinal,ref in enumerate(refs,2):
        if (not isinstance(ref,dict) or set(ref)!={'part','sha256'}
                or ref['part']!=f'reader-presentation-reviewed.part{ordinal}.json'
                or not isinstance(ref['sha256'],str)
                or not re.fullmatch('[a-f0-9]{64}',ref['sha256'])):
            raise ValueError('Invalid sequential Reader Source part reference')
    return refs


def decode_source_parts(raw,read_part,available_parts=None):
    """Verify complete byte inputs before exposing a merged logical registry."""
    base=_parse(raw)
    refs=part_refs(base.pop(MARKER)) if MARKER in base else []
    expected={ref['part'] for ref in refs}
    if available_parts is not None and set(available_parts)!=expected:
        raise ValueError('Missing or orphan Reader Source parts')
    for ref in refs:
        content=read_part(ref['part'])
        if len(content)>legacy.MAX_PART_BYTES:raise ValueError('Reader source part exceeds the bounded byte limit')
        if _sha(content)!=ref['sha256']:raise ValueError('Reader Source part checksum differs')
        base=legacy._merge(base,_parse(content))
    return base


def inspect_source(path):
    path=legacy._path(path)
    if path.is_symlink():raise ValueError('Reader Source must not be a symlink')
    if path.stat().st_size>legacy.MAX_PART_BYTES:raise ValueError('Reader source part exceeds the bounded byte limit')
    raw=path.read_bytes();base=_parse(raw)
    refs=part_refs(base[MARKER]) if MARKER in base else []
    expected={ref['part'] for ref in refs}
    found={p.name for p in path.parent.glob('reader-presentation-reviewed.part*.json')}
    if found!=expected:raise ValueError('Missing or orphan Reader Source parts')
    contents={BASE:raw}
    for ref in refs:
        part=path.with_name(ref['part'])
        if part.is_symlink():raise ValueError('Reader Source part must not be a symlink')
        if part.stat().st_size>legacy.MAX_PART_BYTES:raise ValueError('Reader source part exceeds the bounded byte limit')
        content=part.read_bytes()
        if len(content)>legacy.MAX_PART_BYTES:raise ValueError('Reader source part exceeds the bounded byte limit')
        if _sha(content)!=ref['sha256']:raise ValueError('Reader Source part checksum differs')
        contents[part.name]=content
    return tuple(path.with_name(name) for name in contents),contents


def load_source(path):
    paths,contents=inspect_source(path)
    return decode_source_parts(contents[BASE],contents.__getitem__,[p.name for p in paths[1:]])


def _bounded_parts(value,minimum_parts):
    base={**value,**{name:{} for name in TABLES}}
    empty={name:{} for name in TABLES}
    part={name:{} for name in TABLES};size=len(legacy._encoded(empty))
    payloads={};refs=[]
    def finish():
        raw=legacy._encoded(part)
        if len(raw)!=size or len(raw)>legacy.MAX_PART_BYTES:
            raise ValueError('Reader source part exceeds the bounded byte limit')
        name=f'reader-presentation-reviewed.part{len(refs)+2}.json'
        payloads[name]=raw;refs.append({'part':name,'sha256':_sha(raw)})
        if len(refs)>=MAX_PARTS:raise ValueError('Reader Source part count exceeds bound')
    for table in TABLES:
        for key,item in value[table].items():
            weight=len(legacy._encoded({key:item}))-3
            addition=weight+bool(part[table])
            if size+addition>legacy.MAX_PART_BYTES:
                if not any(part.values()):raise ValueError('Indivisible Reader Source entry exceeds bound')
                finish();part={name:{} for name in TABLES};size=len(legacy._encoded(empty));addition=weight
            if size+addition>legacy.MAX_PART_BYTES:
                raise ValueError('Indivisible Reader Source entry exceeds bound')
            part[table][key]=item;size+=addition
    if any(part.values()):finish()
    # Retain already reviewed physical paths on shrink; never strand an old part.
    while len(refs)<max(1,minimum_parts-1):
        part={name:{} for name in TABLES};size=len(legacy._encoded(empty));finish()
    base[MARKER]={'schema':SCHEMA,'parts':refs}
    result={BASE:legacy._encoded(base),**payloads}
    if any(len(raw)>legacy.MAX_PART_BYTES for raw in result.values()):
        raise ValueError('Reader Source metadata/index exceeds the bounded byte limit')
    if decode_source_parts(result[BASE],result.__getitem__,list(result)[1:])!=value:
        raise ValueError('Reader Source multipart semantic parity failed')
    return result


def source_parts(value,split=False,minimum_parts=1,legacy_raw=None):
    if not isinstance(value,dict):raise ValueError('Reader source must be an object')
    if type(minimum_parts) is not int or not 1<=minimum_parts<=MAX_PARTS:
        raise ValueError('Invalid minimum Reader Source part count')
    if MARKER in value:raise ValueError('Reserved split marker is not display data')
    if legacy_raw is not None and (not isinstance(legacy_raw,bytes)
            or json.loads(legacy_raw.decode('utf-8-sig'))!=value):
        raise ValueError('Legacy Reader Source bytes differ from logical data')
    if minimum_parts<=2:
        if not split and minimum_parts==1:
            raw=legacy._encoded(value) if legacy_raw is None else legacy_raw
            if len(raw)<=legacy.MAX_PART_BYTES:return {BASE:raw}
        try:
            return legacy.serialized_parts(value,True)
        except ValueError as error:
            if str(error)!='Two Reader source parts exceed the bounded byte limit':raise
    if any(not isinstance(value.get(name),dict) for name in TABLES):
        raise ValueError('Reader source tables must remain objects')
    return _bounded_parts(value,minimum_parts)


def write_source(path,value,split=None,legacy_raw=None):
    path=legacy._path(path)
    existing=inspect_source(path)[0] if path.exists() else ()
    if not existing and any(path.parent.glob('reader-presentation-reviewed.part*.json')):
        raise ValueError('Orphan Reader Source parts without primary')
    if split is False and len(existing)>1:
        raise ValueError('Explicit collapse must preserve/review every Source part')
    payloads=source_parts(value, bool(split) if split is not None else len(existing)>1,
                          max(1,len(existing)),legacy_raw=legacy_raw)
    if not {p.name for p in existing}<=set(payloads):raise ValueError('Refuse to strand a Reader Source part')
    path.parent.mkdir(parents=True,exist_ok=True)
    # Write all secondary files first. Any interrupted update remains fail-closed
    # through old checksums or orphan detection until the pinned primary is last.
    for name in [n for n in payloads if n!=BASE]+[BASE]:
        target=path.with_name(name);tmp=target.with_name(name+'.reader-tmp')
        if target.is_symlink() or tmp.exists():raise ValueError('Unsafe or interrupted Reader Source write')
        with tmp.open('xb') as stream:stream.write(payloads[name])
        os.replace(tmp,target)
