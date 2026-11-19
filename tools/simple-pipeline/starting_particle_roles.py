"""Owner W rules: deterministic names/roles, never model-derived.

Only a same-record exact component identity is eligible. Raw excerpts, if
supplied by the local saved CHECK archive, must stay in that archive.
"""
from collections import Counter
from copy import deepcopy
import re
import unicodedata


STARTING = 'starting_particles'
SUB = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')
PARTICLE = r'core|qds?|quantum[ -]+dots?|nano[ -]?(?:particles?|crystals?)|seeds?|bulk|powders?'
PREFIX = re.compile(r'^(?:as[ -]+prepared|bulk|powder)\b[ -]*', re.I)
SUFFIX = re.compile(r'\s+(?:'+PARTICLE+r')$', re.I)
SHELL = re.compile(r'\s+shell(?:\s+layer)?$', re.I)


def literal(value):
    return unicodedata.normalize('NFC',value or '').translate(SUB).strip()


def cleanup(name):
    """Repair only the documented dropped-glyph spelling; not plain terpineol."""
    if re.fullmatch(r'\s*\u0328\s*[-‐‑–]\s*terpineol\s*',name,re.I):
        return 'α-terpineol', False
    suspicious = bool(re.match(r'^\s*[\u0300-\u036f�]',name))
    return name, suspicious


def strip_particle(name):
    tail = name
    while True:
        rest = SUFFIX.sub('',PREFIX.sub('',tail)).strip()
        if rest == tail:
            return rest, rest != name
        tail = rest


def ready_made(formula, quotes):
    # Match a charged/added ready-made particle phrase, not a shell formation
    # statement that happens to use the words 'particle' and 'added'.
    name = re.escape(formula)
    particles = rf'(?:preformed|pre[ -]prepared|as[ -]prepared|commercial)\s+{name}\s+(?:{PARTICLE})|{name}\s+(?:{PARTICLE})'
    added = r'add(?:ed|ing)?|introduc(?:e|ed|ing)|inject(?:ed|ing)?|charg(?:e|ed|ing)|dispers(?:e|ed|ing)|mix(?:ed|ing)?'
    for text in quotes:
        q = literal(text)
        # Formula match stays case-sensitive (Co and CO are not the same).
        if re.search(rf'(?i:\b(?:{added})\s+(?:the\s+)?)(?:{particles})\b',q):
            return True
        if re.search(rf'\b(?:{particles})\s+(?i:(?:was|were|are)\s+(?:{added}))\b',q):
            return True
    return False


def role_for(name, material, quotes=()):
    name = literal(name)
    formula = literal(material.get('formula'))
    components = list(dict.fromkeys(literal(x) for x in material.get('components',[])))
    is_core_shell = material.get('architecture') == 'core_shell'
    core = components[0] if is_core_shell and len(components)>1 else None
    shells = set(components[1:]) if core else set()
    known = {formula, *components} - {''}
    layer = SHELL.sub('',name)
    if layer != name and layer in shells:
        return ('start',layer) if ready_made(layer,quotes) else ('omit',layer)
    base, described = strip_particle(name)
    if base in shells:
        return ('start',base) if described or ready_made(base,quotes) else ('omit',base)
    if base in known and (described or base in (formula,core)):
        return 'start',base
    return 'unchanged',None


def union(left,right):
    return list(left)+[row for row in right if row not in left]


def revise(source, quotes_by_id=None):
    """Return modified canonical record plus a quote-free reversible action ledger.

    Do not overwrite the input. Amount-bearing omitted layers or non-simple
    graph references must be resolved explicitly by the caller before release.
    """
    if source['quality']['review_status'] != 'source_extracted':
        raise ValueError('W may not alter reviewed records')
    quotes_by_id = quotes_by_id or {}
    record = deepcopy(source)
    kept, groups, map_id, ledger, holds = [], {}, {}, [], []
    for row in record['materials']:
        rid = row['id']
        name, unresolved = cleanup(row['name'])
        if name != row['name']:
            ledger.append(('W4',rid,rid))
            row['name'] = name
        if unresolved:
            ledger.append(('W4_unresolved',rid,rid))
        result, key = role_for(row['name'],record['material'],quotes_by_id.get(rid,()))
        if result == 'omit':
            if row['quantities']:
                holds.append(('W2_quantity',rid))
            ledger.append(('W2',rid,None))
            map_id[rid] = None
            continue
        if result == 'start':
            if row['role'] != STARTING:
                ledger.append(('W1',rid,rid))
                row['role'] = STARTING
            if key in groups:
                old = groups[key]
                if row['identity'] != old['identity'] or (
                    row['formula'] and old['formula'] and row['formula'] != old['formula']):
                    holds.append(('W3_identity_conflict',rid))
                if old['formula'] is None: old['formula'] = row['formula']
                old['evidence'] = union(old['evidence'],row['evidence'])
                old['notes'] = union(old['notes'],row['notes'])
                for kind,quantity in row['quantities'].items():
                    field, i = kind,2
                    while field in old['quantities'] and old['quantities'][field] != quantity:
                        field = f'{kind}_{i}'; i += 1
                    old['quantities'][field] = quantity
                map_id[rid] = old['id']
                ledger.append(('W3',rid,old['id']))
                continue
            groups[key] = row
        kept.append(row)
    record['materials'] = kept
    merged_targets = set(map_id.values()) - {None}
    def remap(ids):
        # W only changes references to omitted or joined entries. A generic
        # deduplication would silently change previously checked inputs.
        out, seen = [], set()
        for mid in ids:
            resolved = map_id.get(mid, mid)
            if resolved is None or (resolved in merged_targets and resolved in seen):
                continue
            out.append(resolved)
            seen.add(resolved)
        return out
    for operation in record['operations']:
        for field in ('inputs','optional_inputs'):
            if field in operation: operation[field] = remap(operation[field])
    for state in record['material_states']:
        state['parent_ids'] = remap(state['parent_ids'])
    if any(c['material_id'] in map_id for stock in record['stocks'] for c in stock['components']):
        holds.append(('stock_reference',''))
    if any(c.get('chemical_material_id') in map_id for c in record['condition_options']):
        holds.append(('condition_option_reference',''))
    return record, {'entries':ledger,'holds':holds,'counts':dict(Counter(x[0] for x in ledger))}
