"""Owner W10: join unquantified duplicates with the same cleaned name, role and stage."""
from collections import defaultdict
from copy import deepcopy

from starting_particle_roles import cleanup, literal


def material_key(material):
    return literal(cleanup(material['name'])[0]), material['role'], material['stage']


def compatible_charge_tie(indices, materials):
    rows=[materials[i] for i in indices]
    return len({material_key(r) for r in rows})==1 and sum(bool(r['quantities']) for r in rows)<=1


def join_materials(source):
    if source['quality']['review_status']!='source_extracted':
        raise ValueError('W10 may not change reviewed records')
    record=deepcopy(source);rows=record['materials'];groups=defaultdict(list)
    for row in rows:groups[material_key(row)].append(row)
    remap={}
    for peers in groups.values():
        if len(peers)<2:continue
        # Keep multiple checked charges distinct. Unquantified peers join
        # the first charge, if any; otherwise retain the first stable ID.
        keep=next((r for r in peers if r['quantities']),peers[0])
        for other in peers:
            if other is keep or other['quantities']:continue
            assert other['id']!=keep['id'] and other['id'] not in remap
            formula=other.get('formula')
            if formula and keep.get('formula') not in (None,formula):
                raise ValueError('Duplicate names have conflicting material formulae')
            if formula:keep['formula']=formula
            for key,value in other.get('identity',{}).items():
                if value is None:continue
                if keep['identity'].get(key) not in (None,value):
                    raise ValueError('Duplicate names have conflicting material identities')
                keep['identity'][key]=value
            for field in ('notes','evidence'):
                for value in other[field]:
                    if value not in keep[field]:keep[field].append(value)
            supported={'id','name','formula','role','stage','identity','quantities','notes','evidence'}
            if any(k not in supported and keep.get(k)!=v for k,v in other.items()):
                raise ValueError('Duplicate entry has an unmatched canonical field')
            remap[other['id']]=keep['id']
    if not remap:return source,{}
    record['materials']=[r for r in rows if r['id'] not in remap]
    targets=set(remap.values())
    def value(x):
        if isinstance(x,str):return remap.get(x,x)
        if isinstance(x,list):
            out=[]
            for i in x:
                v=value(i)
                if not (isinstance(v,str) and v in targets and v in out):out.append(v)
            return out
        if isinstance(x,dict):
            out={}
            for k,v in x.items():
                key=remap.get(k,k);resolved=value(v)
                if key in out and out[key]!=resolved:
                    raise ValueError('Duplicate IDs index distinct canonical values')
                out[key]=resolved
            return out
        return x
    return value(record),remap
