"""Search terms from declared chemicals only; independent of P grouping."""
import re

from method_families import author_label,excluded_source,fixed_name_alias,fixed_source_identity,source_identity

EXCLUDED={'starting particles','grown layer','substrate'}
EXPLICIT=re.compile(r'\b(?:precursor|source|feed)\b',re.I)


def method_search(record):
    source=record['sources'][0]
    names=set()
    for material in record.get('materials',[]):
        role=re.sub(r'[_-]+',' ',str(material.get('role')or'')).strip().lower()
        if role in EXCLUDED or material.get('stage')=='workup' or excluded_source(material):continue
        fixed=fixed_source_identity(material)
        if not (fixed or EXPLICIT.search(role)):continue
        resolved=fixed or source_identity(material)
        own,_=fixed_name_alias(material.get('name'))
        for value in (material.get('name'),material.get('formula'),(resolved or {}).get('label'),(own or {}).get('label')):
            if isinstance(value,str) and 0<len(value.strip())<=160:names.add(value.strip())
    return {'source_citation':author_label(source.get('authors'),source.get('year')),
            'method_source_names':sorted(names,key=lambda x:(x.casefold(),x))}
