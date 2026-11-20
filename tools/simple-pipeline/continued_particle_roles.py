"""Owner W7/W8 determinations from one exact source-extracted record."""
import re
import unicodedata

VAPOR=re.compile(r'\b(?:mbe|mocvd|movpe|cvd|ald|epitax(?:y|ial(?:ly)?)|sputter(?:ing|ed)?|'
    r'chemical[\s-]+vapou?r[\s-]+deposition|atomic[\s-]+layer[\s-]+deposition|'
    r'pulsed[\s-]+laser[\s-]+deposition|thermal[\s-]+evaporation|stranski[\s-]+krastanov)\b',re.I)
SUBSTRATE=re.compile(r'\b(?:substrates?|wafers?|buffers?)\b',re.I)
PARTICULATE=re.compile(r'\b(?:qds?|quantum[ -]+dots?|nano[ -]?(?:crystals?|particles?)|seeds?)\b',re.I)
METAL={'metal_precursor','metal_source','cation_precursor','cation_source','host_precursor',
       'dopant_precursor','metalloid_precursor'}
NONMETAL={'chalcogen_precursor','chalcogen_source','pnictogen_precursor','pnictogen_source',
          'nonmetal_precursor','nonmetal_source','anion_precursor','anion_source','halide_precursor'}
NONMETAL_ELEMENTS=set('H B C N O F Si P S Cl As Se Br Te I At Sb'.split())
SUBS=str.maketrans('₀₁₂₃₄₅₆₇₈₉','0123456789')


def exact_formula(value):
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',value or '').translate(SUBS))


def elements(value):
    # Only an explicit formula is parsed: don't read elements out of a name.
    v=exact_formula(value)
    if not re.fullmatch(r'[A-Z][A-Za-z0-9.·()\[\]+\-/]*',v):return set()
    return set(re.findall('[A-Z][a-z]?',v))


def is_vapor(record):
    terms=[record.get('method') or '']
    for step in record.get('operations') or []:
        terms.extend(step.get(k) or '' for k in ('action','label','description'))
    return any(VAPOR.search(x.replace('−','-').replace('–','-')) for x in terms)


def product_precursor(rows,target,product_elements):
    for r in rows:
        role=(r.get('role') or '').replace(' ','_').replace('-','_')
        n=r.get('name') or ''
        if exact_formula(n)==target or PARTICULATE.search(n) or role not in METAL|NONMETAL:continue
        known=elements(r.get('formula'))
        if known and product_elements:
            allowed=product_elements&(NONMETAL_ELEMENTS if role in NONMETAL else product_elements-NONMETAL_ELEMENTS)
            if not known&allowed:continue
        # Existing explicit checked role is sufficient when its formula is
        # unavailable. No inference from a name that simply mentions a metal.
        return True
    return False


def context(record):
    material=record['material']
    formula=exact_formula(material.get('formula'))
    components={exact_formula(x) for x in material.get('components',[])}|{formula}
    return {'vapor':is_vapor(record),'formula':formula,'components':components-{''},
        'precursors':product_precursor(record['materials'],formula,
                       set(material.get('elements') or []) or elements(formula))}


def exact_substrate_in_name_or_quote(name,quotes):
    if SUBSTRATE.search(name):return True
    # A formula-only converter name may be the exact formula part of a
    # checked phrase with explicit wafer/buffer/substrate terminology.
    # This does not promote an incidental mention elsewhere in the text.
    if not elements(name):return False
    f=re.escape(exact_formula(name))
    return any(re.search(rf'(?<![\w]){f}(?![\w])\s*(?:\([0-9 -]+\)\s*)?(?i:substrates?|wafers?|buffers?)\b',
                         unicodedata.normalize('NFKC',q)) for q in quotes)


def override(row,scope,quotes=()):
    n=row['name'];v=exact_formula(n)
    if scope['vapor']:
        if PARTICULATE.search(n):return None
        if exact_substrate_in_name_or_quote(n,quotes):return 'W7_substrate','substrate'
        if v in scope['components']:return 'W7_grown_layer','grown_layer'
        return None
    if scope['precursors'] and v and v==scope['formula']:
        return 'W8',None
    return None
