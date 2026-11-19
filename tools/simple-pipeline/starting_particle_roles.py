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
PARTICLE = r'cores?|qds?|quantum[ -]+dots?|nano[ -]?(?:particles?|crystals?)|seeds?|bulk|powders?'
PREFIX = re.compile(r'^(?:as[ -]+prepared|bulk|powder)\b[ -]*', re.I)
SUFFIX = re.compile(r'\s+(?:'+PARTICLE+r')$', re.I)
SHELL = re.compile(r'\s+shells?(?:\s+layers?)?$', re.I)
SAMPLE_LABEL = re.compile(r'\s+\(([A-Za-z0-9][A-Za-z0-9.-]{0,23})\)$')


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


def particle_name(name):
    """A sample label may follow a particle descriptor, but not a bare formula."""
    label = SAMPLE_LABEL.search(name)
    if label and strip_particle(name[:label.start()])[1]:
        return name[:label.start()], label.group(1)
    return name, None


def physical_form(name):
    stem, label = particle_name(literal(name))
    if re.search(r'\bseeds?$', stem, re.I):
        return 'seed', label
    if re.search(r'\bpowders?\b', stem, re.I):
        return 'powder', label
    if label:
        return 'named', label
    return None


def alias_form(base, quotes, choices):
    """Bind a bare alias to an explicit physical input only with unique support."""
    matched = set()
    for form in choices:
        kind, label = form
        if label:
            # Printed labels can use a hyphen or a space. Keep short symbols
            # bounded so one sample label cannot pick up a longer one.
            token = r'[\s-]+'.join(re.escape(part) for part in label.split('-'))
        elif kind == 'powder':
            token = r'powders?'
        else:
            token = r'seeds?'
        formula = re.escape(base)
        gap = r'[^;.!?\n]{0,80}'
        if any(re.search(rf'\b{formula}\b{gap}(?i:\b{token}\b)|(?i:\b{token}\b){gap}\b{formula}\b', literal(q)) for q in quotes):
            matched.add(form)
    return next(iter(matched)) if len(matched) == 1 else None


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
    base, described = strip_particle(particle_name(name)[0])
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
    prepared = []
    explicit = {}
    explicit_targets = {}
    for row in record['materials']:
        rid = row['id']
        name, unresolved = cleanup(row['name'])
        if name != row['name']:
            ledger.append(('W4',rid,rid))
            row['name'] = name
        if unresolved:
            ledger.append(('W4_unresolved',rid,rid))
        result, key = role_for(row['name'],record['material'],quotes_by_id.get(rid,()))
        form = physical_form(row['name']) if result == 'start' else None
        if form is not None:
            explicit.setdefault(key, set()).add(form)
            explicit_targets.setdefault((key, form), row['id'])
        prepared.append((row, result, key, form))
    # Record order cannot make a bare alias erase an explicitly named input.
    # Collect over the original rows; process bound aliases after their targets.
    bindings = {}
    for row, result, base, form in prepared:
        if result == 'start' and form is None and literal(row['name']) == base:
            bound = alias_form(base, quotes_by_id.get(row['id'], ()), explicit.get(base, ()))
            if bound is not None:
                bindings[row['id']] = explicit_targets[(base, bound)]
    by_id = {row['id']: row for row, _, _, _ in prepared}
    for row, result, key, form in prepared:
        rid = row['id']
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
            # Different explicit physical forms are never synonyms merely
            # because the formula is the same. An alias may point to its exact
            # target before or after it in the original inventory.
            group_key = (key, form)
            if rid in bindings or group_key in groups:
                old = by_id[bindings[rid]] if rid in bindings else groups[group_key]
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
            groups[group_key] = row
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
