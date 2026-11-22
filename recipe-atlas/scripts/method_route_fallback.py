"""Bind P fallbacks to existing J identities and conservative explicit routes.

Preview helper; the native release will apply the same small changes to the
method-family builder, not patch global functions at runtime.
"""
import re

from method_recipe_patterns import all_precursor_ids, declared_sources, family_order, recipe_class


def source_fallback(J,prior,record,element,metal,context=None):
    old,reason=prior(record,element,metal,context)
    if old or reason!='missing_source':return old,reason
    # A role on a product, another sample, a substrate or a workup reagent
    # cannot supply a precursor. J exact normalization is for the label, not
    # for collapsing separate candidate compounds before applying P1(c).
    product=record.get('material') or {};pname=product.get('formula') or ''
    names={J.norm(n) for n in [product.get('name'),*(p.get('name') for p in record.get('products',[]))] if n}
    def exclude(m):
        formula=m.get('formula') or m.get('name') or ''
        return J.excluded_source(m) or J.norm(m.get('name')) in names or bool(pname and J.formula_equivalent(pname,formula))
    def identity(m):
        named,conflicting=J.fixed_name_alias(m.get('name'))
        if conflicting:return None
        fixed=J.fixed_source_identity(m)
        pinned=J.pinned_source_identity(record,m,context)
        own=fixed or pinned or J.source_identity(m)
        if not own:return None
        identity=pinned or named or own
        # Preserve selenium and the phosphine selenide as different molecular
        # compounds even when J shows both under generic selenium supply.
        own_name=J.norm(m.get('name'))
        phosphine={'topse':'topse','trioctylphosphineselenide':'topse',
                   'tbpse':'tbpse','tributylphosphineselenide':'tbpse'}.get(own_name)
        if phosphine:identity={'key':'phosphine:'+phosphine}
        elements=own.get('source_elements') or own.get('elements') or set()
        label=J.family_source(own)
        return {'key':identity['key'],'elements':elements,'family':{'key':label['key'],'label':label['label']}}
    result=declared_sources(record,element,metal,identity=identity,excluded_source=exclude)
    return (result['family'],None) if result else (old,reason)


def operation_fallback(J,prior,record,override=None):
    explicit=prior(record,override)
    if explicit:return explicit
    # Distinguish a truly generic method from a negated or conflicting one.
    labels=[record.get('method'),override,J.route_label(record)]
    for o in record.get('operations',[]):
        labels.extend([o.get('label'),o.get('vessel'),o.get('system')])
    method_labels=[str(x or '').replace('_',' ') for x in labels[:3]]
    system_labels=[str(x or '') for x in labels[3:]]
    explicit_patterns=[pat for _,pat in J.NAMED_METHODS+J.ROUTE_CLASSES]
    if any(re.search(pat,value,re.I) for value in method_labels for pat in explicit_patterns):return ''
    if any(re.search(pat,value,re.I) for value in system_labels for _,pat in J.ROUTE_CLASSES[7:10]):return ''
    target=J.target_sources(str((record.get('material') or {}).get('formula') or ''))
    named=[]
    if target:
        metal,nonmetals=target
        named=all_precursor_ids(record.get('materials',[]),metal,nonmetals,
                                role_matches=J.role_matches,excluded_source=J.excluded_source)
    return recipe_class(record,named)


def sort_result(result):
    groups=sorted(result['families'],key=family_order)
    return {**result,'families':groups,'default_record_id':groups[0]['default_record_id'] if groups else None}
