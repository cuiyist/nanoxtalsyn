"""Q candidate selector and validation for the existing Reader projection."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re
import sys

from chemical_reference_identity import material_context_reason
from method_families import NAMED_METHODS, ROUTE_CLASSES, route

SCHEMA_Q='mattersyn-reader-background-library/2'
LABEL="General background, not the authors' interpretation"
MISSING={'starting particles','grown layer','substrate'}
PRIORITY={'pair':0,'reagent':1,'route':2}


def identity_key(token):return ('cid' if token[0]=='CID' else token[0])+':'+str(token[1])


def validated(library):
    if library.get('schema')!=SCHEMA_Q or library.get('label')!=LABEL or library.get('limit')!=4:
        raise ValueError('Q schema, disclosure, or card limit is invalid')
    refs=library.get('references') or {};statements=library.get('statements') or []
    for key,r in refs.items():
        doi=r.get('doi','')
        if not (key==doi.casefold() and re.fullmatch(r'10\.\d{4,9}/[^\s<>{}]+',doi)
                and r['url']=='https://doi.org/'+doi and isinstance(r['authors'],list) and r['authors']
                and all(isinstance(x,str) and x.strip() for x in r['authors']) and r['title']
                and type(r['year']) is int and 1500<=r['year']<=2200
                and re.fullmatch(r'[a-f0-9]{64}',r['metadata_response_sha256'])
                and r.get('resolver_redirect_verified') is True and r.get('exact_DOI_metadata_verified') is True
                and r.get('paper_or_abstract_requested') is False):
            raise ValueError('Invalid DOI-only Q metadata: '+key)
    routes={x for x,_ in NAMED_METHODS+ROUTE_CLASSES};unique=set();identities=set()
    for item in statements:
        rid=item.get('id','');body=item.get('summary','');ident=item.get('compound_ids') or []
        allowed={'pair':{2,3},'reagent':{1},'route':{0}}.get(item.get('kind'),set())
        if not (re.fullmatch(r'[a-z][a-z0-9-]+',rid) and rid not in unique and item['topic'] and item['title']
                and item['reference'] in refs and len(ident)==len(set(ident)) and len(ident) in allowed
                and all(isinstance(x,str) and ':' in x and x.split(':',1)[1] for x in ident)
                and type(item.get('priority')) is int and 0<=item['priority']<=100
                and isinstance(item.get('requires_product_elements'),list)
                and all(re.fullmatch(r'[A-Z][a-z]?',x) for x in item['requires_product_elements'])
                and item['route_classes'] and set(item['route_classes'])<=routes and 35<=len(body)<=520
                and not any(c.isdigit() for c in body) and 2<=len(re.findall(r'[.!?](?:\s|$)',body))<=3):
            raise ValueError('Q scope or authored statement invalid: '+rid)
        unique.add(rid);identities.update(ident)
    general=library.get('fallback') or {}
    if len(identities)<60 or general.get('id')!='general-context' or general.get('kind')!='fallback' or general.get('reference') not in refs:
        raise ValueError('Q lacks required identity coverage or the unchanged M fallback')
    return library


@lru_cache(maxsize=2)
def identity_projection(atlas):
    path=Path(atlas).resolve();chemical=path/'static/assets/chemical-registry'
    helper=path.parent/'tools/simple-pipeline'
    sys.path.insert(0,str(helper))
    from completeness_identity import ChemicalIdentity
    entries=json.loads((chemical/'registry.json').read_bytes())['entries']
    alias=ChemicalIdentity(entries);ident={}
    for entry in entries:
        if material_context_reason(entry) is not None or entry.get('depictionKind') in {'mixture','polymer','equipment','support'}:continue
        values=alias.tokens(entry['name'])
        if len(values)==1:ident[entry['id']]=identity_key(next(iter(values)))
    records=json.loads((chemical/'bindings.json').read_bytes())['recordBindings']
    return alias,ident,records


def match_record(record,projection):
    alias,ident,all_bindings=projection;known=all_bindings.get(record['record_id'],{});found=set()
    for m in record.get('materials',[]):
        if str(m.get('role')or'').replace('_',' ').replace('-',' ').casefold() in MISSING:continue
        valid=ident.get(known.get(m['id']))
        if not valid:continue
        source={identity_key(t) for t in alias.tokens(m.get('name'))}
        if not source or valid in source:found.add(valid)
    return found


def choose(library,identity,own_route,product_elements=()):
    elements=set(product_elements)
    matches=[row for row in library['statements'] if own_route in row['route_classes'] and set(row['compound_ids'])<=identity
             and set(row['requires_product_elements'])<=elements]
    topics=set();selected=[]
    for row in sorted(matches,key=lambda x:(PRIORITY[x['kind']],-x['priority'],x['id'])):
        if row['topic'] in topics:continue
        topics.add(row['topic']);selected.append(row)
        if len(selected)==4:break
    return selected or [library['fallback']]


def select_q_background(record,presentation,library,projection):
    identity=match_record(record,projection)
    rows=choose(library,identity,route(record,presentation.get('method_label')),(record.get('material') or {}).get('elements') or [])
    return [{'id':row['id'],'title':row['title'],'summary':row['summary'],'label':LABEL,'reference':deepcopy(library['references'][row['reference']]),
             'reagent_specific':row['kind'] in ('pair','reagent'),'topic':row['topic']} for row in rows]
