"""P draft: source-list and actual operation fallbacks, presentation-only."""
from collections import defaultdict
import re


EXCLUDED_ROLES={'starting_particles','grown_layer','substrate','solvent'}
TYPED_METAL=re.compile(r'\b(?:cation|(?<!non )metal) (?:precursor|source)\b',re.I)
TYPED_NONMETAL=re.compile(r'\b(?:nonmetal|non metal|chalcogen|pnictogen|anion) (?:precursor|source)\b',re.I)
METAL_ROUTES={'Molecular beam epitaxy','Chemical vapour deposition','Other vapour or physical deposition','Solid state'}
SOLUTION_ROUTES={'Hot injection','Heat-up','SILAR','Solvothermal or hydrothermal',
 'Aqueous or colloidal precipitation','Sol-gel','Microwave','Brust','Turkevich/citrate reduction',
 'Stöber','Pechini','Polyol','Chemical reduction','Seed-mediated growth','Cation exchange',
 'Reflux','Microemulsion','Chemical bath deposition','Microfluidic'}


def identity_text(x):return re.sub(r'[^A-Za-z0-9.]+','',str(x or '')).casefold()


def declared_sources(record,element,metal,*,identity,excluded_source,existing=None):
    """Follow P1 only for a genuinely missing main source, never a conflict."""
    if existing is not None:return existing
    product=record.get('material') or {};formula=product.get('formula');whole=identity_text(formula)
    inputs=[]
    for item in record.get('materials',[]):
        role=str(item.get('role') or '').strip().casefold().replace('-','_').replace(' ','_')
        if role in EXCLUDED_ROLES or excluded_source(item) or item.get('stage')=='workup':continue
        if whole and whole in (identity_text(item.get('formula')),identity_text(item.get('name'))):continue
        direct=identity(item)
        typed=(TYPED_METAL if metal else TYPED_NONMETAL).search(role.replace('_',' ')) is not None
        # A resolved compound with a different element cannot be this source.
        # Keep an unresolved explicitly typed label as an ambiguity, however.
        if typed and direct and direct.get('elements') and element not in direct['elements']:typed=False
        inputs.append((typed,direct))
    typed=[x for t,x in inputs if t]
    if typed:
        if any(not i or i.get('elements') and element not in i['elements'] for i in typed):return None
        by_role={x['key']:x for x in typed}
        return next(iter(by_role.values())) if len(by_role)==1 else None
    by_formula={i['key']:i for _,i in inputs if i and element in i.get('elements',())}
    return next(iter(by_formula.values())) if len(by_formula)==1 else None


def all_precursor_ids(materials,metal,nonmetals,*,role_matches,excluded_source):
    """Heat-up requires each target source class, not merely enough entries."""
    required=[set() for _ in range(1+len(nonmetals))]
    for item in materials:
        if item.get('stage')=='workup' or excluded_source(item):continue
        role=re.sub(r'[-_]+',' ',str(item.get('role') or '')).strip().casefold()
        if role.replace(' ','_') in EXCLUDED_ROLES:continue
        if role_matches(item,metal,True) or TYPED_METAL.search(role):
            required[0].add(item['id'])
        for i,element in enumerate(nonmetals,1):
            if role_matches(item,element,False) or len(nonmetals)==1 and TYPED_NONMETAL.search(role):
                required[i].add(item['id'])
    if any(not ids for ids in required):return []
    ids=set.union(*required)
    return sorted(ids) if len(ids)>=len(required) else []


def recipe_class(record,precursor_ids):
    """Class only when one unambiguous allowed operation pattern fits."""
    operations=[o for o in record.get('operations',[]) if o.get('stage','synthesis')=='synthesis']
    states={s['id']:tuple(s.get('parent_ids') or ()) for s in record.get('material_states',[])}
    stocks={s['id']:tuple(x['material_id'] for x in s.get('components',[]) if x.get('material_id')) for s in record.get('stocks',[])}
    material_ids={m['id'] for m in record.get('materials',[])}
    def ancestry(ids):
        pending=list(ids);seen=set()
        while pending:
            key=pending.pop()
            if key in seen:continue
            seen.add(key);pending.extend(states.get(key,()));pending.extend(stocks.get(key,()))
        return seen
    def phrase(o):return ' '.join(str(o.get(k) or '') for k in ('label','description','vessel','system'))
    def heating(o):return bool(re.fullmatch(r'heat(?:_(?:up|mixture|solution|clear|batch|reaction))?|warm(?:_mixture)?',
                                           str(o.get('action') or '').casefold().replace('-','_')))
    def swift(o):
        action=str(o.get('action') or '').casefold().replace('-','_')
        return action.startswith('inject') or action in ('rapid_addition','swift_addition') or (action in ('add','addition') and re.search(r'\b(?:rapidly|swiftly|quickly)\s+(?:added|add)\b',phrase(o),re.I))
    possible=set();heated_outputs=set();cooled_outputs=set();heat_with_all=False
    def hot_upstream(ids):
        pending=list(ids);seen=set()
        while pending:
            key=pending.pop()
            if key in seen or key in cooled_outputs:continue
            seen.add(key)
            if key in heated_outputs:return True
            pending.extend(states.get(key,()))
        return False
    for step in operations:
        info=phrase(step)
        # A later mention of an autoclave elsewhere does not establish sealing.
        if re.search(r'\b(?:sealed|closed)\b.{0,35}\bautoclave\b|\bautoclave\b.{0,35}\b(?:sealed|closed)\b',info,re.I) and not re.search(r'\b(?:not|unsealed|open)\b',info,re.I):
            possible.add('Solvothermal or hydrothermal')
        upstream=ancestry(step.get('inputs') or ())
        if swift(step) and hot_upstream(step.get('inputs') or ()):possible.add('Hot injection')
        if re.match(r'^(?:cool|quench)(?:\b|_)',str(step.get('action') or ''),re.I):
            cooled_outputs.update(s for s in step.get('outputs') or () if s in states)
        if heating(step):
            heated_outputs.update(s for s in step.get('outputs') or () if s in states)
            if precursor_ids and set(precursor_ids)<=upstream&material_ids:heat_with_all=True
    if heat_with_all and not any(swift(o) for o in operations) and 'Solvothermal or hydrothermal' not in possible:
        possible.add('Heat-up')
    return next(iter(possible)) if len(possible)==1 else ''


def family_order(family):
    kind=family['kind'];r=family.get('route')
    blocks={'synthesis':0 if r in SOLUTION_ROUTES else 1,'other':2,'component':3,'processing':4}
    return (blocks[kind],-family['paper_count'],family['earliest_year'],family['label'].casefold(),family['id'])
