"""F5 conversion for policy-bound CHECK documents; no independent-audit claim.

Every distinct checked chemical object is represented. Alias inputs link to the
same chemical, while ambiguous distinct charges fail closed. Only optical fields
that passed their held-out gate are enabled. Existing scientific translation is
delegated to the native Builder.
"""
import copy
from functools import lru_cache
import json
import mattersyn_simple as engine
from completeness_check import overlap
from completeness_identity import ChemicalIdentity
from completeness_policy import calibrated_policy

OPTICAL={'absorption_peak','emission_peak','plqy'}


class AmbiguousChemicalUse(ValueError):
    pass


@lru_cache(maxsize=1)
def registry_identity():
    return ChemicalIdentity()


@lru_cache(maxsize=None)
def builder_class(base):
    class CompleteBuilder(base):
        def __init__(self,doc,include_optical=False):
            policy=calibrated_policy(doc)
            if policy is None:raise ValueError('Calibrated converter requires a bound CHECK policy')
            self.allowed_optics=set(policy['optical_fields'])
            self.variant=policy['adopted_check_variant']
            self.chemical_identity=registry_identity()
            # For this lane, the tested F5 policy, not the legacy opt-in flag,
            # determines optical conversion.
            super().__init__(doc,include_optical=bool(self.allowed_optics))
            numeric_scope=(
                'Only approved numeric fields can be kept from one pass with contiguous source-quote support '
                'and no conflicting value in the other pass; all other numeric fields require agreement. '
                if self.variant==6 else 'Numerical fields still require agreement between the two passes. ')
            self.review_scope=(
                'Processed by two separate local-model extraction passes and the owner-calibrated CHECK V'+str(self.variant)+'. '
                'Chemical names and steps may be retained through source-quote support under that CHECK; '
                +numeric_scope+
                'It has not been independently audited.')

        def record(self,pair,index):
            scoped=copy.deepcopy(pair);structure=scoped.setdefault('structure',{})
            if engine.has_misattributed_optical_size(structure):
                structure.pop('size')
            for key in OPTICAL-self.allowed_optics:structure.pop(key,None)
            record=super().record(scoped,index)
            if record is None:return None
            recipe=pair.get('recipe') or {};checked=[];seen=set()
            for chemical in recipe.get('chemicals') or []:
                key=json.dumps(chemical,sort_keys=True,ensure_ascii=False)
                if key not in seen:checked.append(chemical);seen.add(key)
            materials=[];used_ids=set()
            for chemical in checked:
                probe=copy.deepcopy(scoped)
                probe['recipe']={**probe.get('recipe',{}),'chemicals':[chemical],'steps':[]}
                translated=super().record(probe,index)
                if translated is None or len(translated['materials'])!=1:
                    raise ValueError('Checked chemical did not map to one native material')
                material=translated['materials'][0];base_id=material['id'];suffix=2
                while material['id'] in used_ids:
                    material['id']=base_id+'--checked-'+str(suffix);suffix+=1
                used_ids.add(material['id']);materials.append(material)
            names=[c['name'] for c in checked]+[u for s in recipe.get('steps') or [] for u in s.get('uses') or [] if isinstance(u,str)]
            identity=self.chemical_identity.context(names);used_before=set()
            for n,(step,operation,state) in enumerate(zip(recipe.get('steps') or [],record['operations'],record['material_states'])):
                ids=[]
                for use in step.get('uses') or []:
                    if not isinstance(use,str):continue
                    matches=[i for i,c in enumerate(checked) if identity.same(use,c['name'])]
                    exact=[i for i in matches if engine.clean(use).casefold()==engine.clean(checked[i]['name']).casefold()]
                    if exact:matches=exact
                    if len(matches)>1:
                        ranks={i:overlap(step.get('quote') or '',checked[i].get('quote') or '') for i in matches}
                        original=matches;best=max(ranks.values());matches=[i for i in matches if ranks[i]==best]
                        if best<.5 or len(matches)!=1:
                            from w10_materials import compatible_charge_tie
                            if not compatible_charge_tie(original,materials):
                                raise AmbiguousChemicalUse('Distinct checked charges lack unique source-quote use binding')
                            matches=[next((i for i in original if materials[i]['quantities']),original[0])]
                    if len(matches)==1:
                        material=materials[matches[0]];mid=material['id']
                        if mid not in ids:ids.append(mid)
                        if operation['stage']=='workup' and mid not in used_before:material['stage']='workup'
                        used_before.add(mid)
                parent=[record['material_states'][n-1]['id']] if n else []
                state['parent_ids']=parent+ids;operation['inputs']=parent+ids
            record['materials']=materials
            for key in OPTICAL-self.allowed_optics:
                label=key.replace('_',' ').capitalize()
                record['quality']['missing_fields']=[s for s in record['quality']['missing_fields'] if not s.startswith(label+' not reported')]
            if self.variant>=2:record['quality']['review_scope']=self.review_scope
            if len(record['materials'])!=len(checked):raise ValueError('Checked chemical conservation failed')
            return record
    return CompleteBuilder
