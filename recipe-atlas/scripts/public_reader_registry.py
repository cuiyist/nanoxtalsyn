"""Bounded public Reader files; preserve every opaque logical entry exactly."""
import hashlib,json,re
from reader_presentation_registry import serialized_parts,_merge
from reader_presentation_registry import BASE as SOURCE_BASE,PART as SOURCE_PART,MARKER,TABLES
BASE='reader-presentation.json'
PART='reader-presentation.part2.json'
MAX_PART_BYTES=80*1024*1024
MULTIPART_SCHEMA='reader-presentation-parts/1'
MAX_PARTS=1024

def encoded(value):
    return (json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8')

def part_refs(marker):
    """Accept legacy or sequential fixed-name parts, never arbitrary URLs/paths."""
    if not isinstance(marker,dict):raise ValueError('Invalid public Reader split marker')
    if set(marker)=={'schema','part','sha256'} and marker['schema']=='reader-presentation-two-part/1':
        refs=[{'part':marker['part'],'sha256':marker['sha256']}]
    elif set(marker)=={'schema','parts'} and marker['schema']==MULTIPART_SCHEMA:
        refs=marker['parts']
    else:raise ValueError('Invalid public Reader split marker')
    if not isinstance(refs,list) or not 1<=len(refs)<=MAX_PARTS:
        raise ValueError('Invalid public Reader part count')
    for index,ref in enumerate(refs,2):
        if (not isinstance(ref,dict) or set(ref)!={'part','sha256'}
                or ref['part']!=f'reader-presentation.part{index}.json'
                or not isinstance(ref['sha256'],str)
                or not re.fullmatch(r'[0-9a-f]{64}',ref['sha256'])):
            raise ValueError('Invalid public Reader split marker')
    return refs

def load_public_parts(raw,read_part):
    """Read and verify all parts before exposing the complete logical view."""
    if len(raw)>=MAX_PART_BYTES:raise ValueError('Public Reader parts must each remain below80MiB')
    value=json.loads(raw)
    if not isinstance(value,dict) or any(not isinstance(value.get(k),dict) for k in TABLES):
        raise ValueError('Public Reader tables must remain objects')
    if MARKER not in value:return value
    refs=part_refs(value.pop(MARKER))
    for ref in refs:
        raw=read_part(ref['part'])
        if len(raw)>=MAX_PART_BYTES:raise ValueError('Public Reader parts must each remain below80MiB')
        if hashlib.sha256(raw).hexdigest()!=ref['sha256']:
            raise ValueError('Public Reader part checksum differs')
        value=_merge(value,json.loads(raw))
    return value

def _bounded_parts(value):
    # Only overflow uses an index plus as many bounded data parts as needed.
    # Entries stay indivisible, in their original table/key order. Byte accounting
    # includes UTF-8, escaping, commas, braces and the final newline exactly.
    base={**value,**{name:{} for name in TABLES}}
    empty={name:{} for name in TABLES}
    part={name:{} for name in TABLES};size=len(encoded(empty));payloads={};refs=[]
    def finish():
        raw=encoded(part)
        if len(raw)!=size or len(raw)>=MAX_PART_BYTES:
            raise ValueError('Public Reader parts must each remain below80MiB')
        name=f'reader-presentation.part{len(refs)+2}.json'
        payloads[name]=raw
        refs.append({'part':name,'sha256':hashlib.sha256(raw).hexdigest()})
        if len(refs)>MAX_PARTS:raise ValueError('Public Reader part count exceeds bound')
    for table in TABLES:
        for key,item in value[table].items():
            weight=len(encoded({key:item}))-3
            addition=weight+bool(part[table])
            if size+addition>=MAX_PART_BYTES:
                if not any(part.values()):
                    raise ValueError('Indivisible Public Reader entry must remain below80MiB')
                finish();part={name:{} for name in TABLES};size=len(encoded(empty))
                addition=weight
            if size+addition>=MAX_PART_BYTES:
                raise ValueError('Indivisible Public Reader entry must remain below80MiB')
            part[table][key]=item;size+=addition
    if any(part.values()):finish()
    base[MARKER]={'schema':MULTIPART_SCHEMA,'parts':refs}
    payloads={BASE:encoded(base),**payloads}
    if load_public_parts(payloads[BASE],payloads.__getitem__)!=value:
        raise ValueError('Public Reader split semantic parity failed')
    return payloads

def public_parts(value,legacy_raw=None):
    if MARKER in value:raise ValueError('Reserved split marker is not logical display data')
    if any(not isinstance(value.get(k),dict) for k in ('records','materials','figures_by_source')):
        raise ValueError('Public Reader tables must remain objects')
    raw=encoded(value) if legacy_raw is None else legacy_raw
    if json.loads(raw)!=value:raise ValueError('Legacy public Reader bytes differ from logical data')
    if len(raw)<MAX_PART_BYTES:return {BASE:raw}
    # Keep the existing two-file bytes/schema wherever they fit. Overflow uses
    # the same logical tables, not truncation or record/figure rewriting.
    try:source=serialized_parts(value,split=True)
    except ValueError as error:
        if str(error)!='Two Reader source parts exceed the bounded byte limit':raise
        return _bounded_parts(value)
    base=json.loads(source[SOURCE_BASE]);part=source[SOURCE_PART]
    base[MARKER]['part']=PART
    payloads={BASE:encoded(base),PART:part}
    if any(len(raw)>=MAX_PART_BYTES for raw in payloads.values()):
        return _bounded_parts(value)
    logical=dict(base);logical.pop(MARKER)
    if _merge(logical,json.loads(part))!=value:
        raise ValueError('Public Reader split semantic parity failed')
    if base[MARKER]['sha256']!=hashlib.sha256(part).hexdigest():
        raise ValueError('Public Reader part checksum differs')
    return payloads
