"""Owner-calibrated cumulative CHECK variants; adopted policy is configured separately.

V0 is the unchanged native function. V1-V5 preserve numeric agreement.
V6 adds only decision-bound numeric fields to the V5 entities.
"""
import collections
import difflib
import re
import mattersyn_simple as e
from completeness_identity import ChemicalIdentity


class QuoteIndex:
    def __init__(self,text):
        # Unicode lowercasing can expand one code point (e.g. dotted capital I).
        # Both offsets and numeric-run checks must use that same normalized text.
        self.text=text;self.clean=e.clean(text).lower();self.letters=e.letters(text)
        self.offsets=[i for i,ch in enumerate(self.clean) if ch.isalnum()]
        self.matcher=difflib.SequenceMatcher(None,autojunk=False);self.matcher.set_seq2(self.letters)
        self.page_of=e.page_finder(text);self.cache={}

    def support(self,quote,near=False):
        key=(quote,near)
        if key in self.cache:return self.cache[key]
        pos=e.find_quote(quote,self.letters)
        if pos>=0:result={'found':True,'near':False,'position':pos,'page':self.page_of(quote)}
        else:
            q=e.letters(quote);self.matcher.set_seq1(q)
            block=self.matcher.find_longest_match(0,len(q),0,len(self.letters))
            found=bool(near and len(q)>=8 and block.size/len(q)>=.9)
            result={'found':found,'near':found,'position':block.b if found else -1,'page':None}
            if found:
                start=self.offsets[block.b];end=self.offsets[block.b+block.size-1]+1
                result.update(raw_start=start,raw_end=end)
                markers=list(re.finditer(r'\[page (\d+)\]\n',self.clean[:start]))
                result['page']=int(markers[-1][1]) if markers else None
        self.cache[key]=result
        return result

    def number_in_run(self,value,support):
        start,end=support['raw_start'],support['raw_end']
        pattern=r'(?<![\w.])\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+'
        for m in re.finditer(pattern,self.clean):
            if start<=m.start() and m.end()<=end and e.same_number(value,float(m[0].replace(',','')),1e-6):return True
        return any(e.same_number(value,n,1e-6) and any(start<=m.start() and m.end()<=end for m in re.finditer(r'\b'+word+r'\b',self.clean,re.I)) for word,n in e.WORDS.items())

    def problem(self,field,fact,variant):
        why=e.fact_problem(field,fact,self.letters)
        if why!='quote not in paper' or variant<4:return why
        support=self.support(fact.get('quote') or '',True)
        if not support['found']:return why
        value=fact['value']
        if field in e.NUMERIC or isinstance(value,(int,float)):
            if not isinstance(value,(int,float)) or isinstance(value,bool):return 'not a number'
            if not self.number_in_run(value,support):return 'number not in supported run'
            canonical=e.to_canonical(value,fact.get('unit'),field);lo,hi=e.LIMITS.get(field,(float('-inf'),float('inf')))
            if canonical is None or canonical!=canonical or not lo<=canonical<=hi:return 'unit or range'
        return None


def overlap(left,right):
    a,b=e.letters(left),e.letters(right)
    if min(len(a),len(b))<8:return 0
    return difflib.SequenceMatcher(None,a,b,autojunk=False).find_longest_match().size/min(len(a),len(b))


def numeric_steps_agree(left,right):
    return all(right.get(k) is None and left.get(k) is None or e.facts_agree(k,e.step_fact(left,k),e.step_fact(right,k))
               for k in ('temperature','time') if left.get(k) is not None or right.get(k) is not None)


def chemical_amount(left,right,index,variant):
    if right is None or left.get('amount') is None:return {}
    fact={'value':left['amount'],'unit':left.get('unit'),'quote':left.get('quote')}
    other={'value':right.get('amount'),'unit':right.get('unit')}
    if (index.problem('amount',fact,variant) is None and e.facts_agree('amount',fact,other)
        and e.squash(left.get('unit') or '')==e.squash(right.get('unit') or '')):
        return {'amount':left['amount'],'unit':left.get('unit') or ''}
    return {}


def check(text,pass_a,pass_b,variant,registry=None):
    assert variant in range(7)
    assert e.check_pass_shape_valid(pass_a) and e.check_pass_shape_valid(pass_b),'whole-pass shape admission unchanged'
    if variant==6:
        from completeness_numbers import check_v6
        from completeness_policy import load_policy
        policy=load_policy()
        if policy['adopted_check_variant']!=6:raise ValueError('V6 is not adopted by the active CHECK policy')
        return check_v6(text,pass_a,pass_b,registry,policy['single_pass_fields'])
    if variant==0:
        stats=collections.Counter();return e.check_paper(text,pass_a,pass_b,stats)
    registry=registry or ChemicalIdentity();idx=QuoteIndex(text);final=[]
    for a,b in e.match_pairs(pass_a['pairs'],pass_b['pairs']):
        if b is None:continue
        ar,br=a.get('recipe') or {},b.get('recipe') or {}
        ac,bc=ar.get('chemicals') or [],br.get('chemicals') or []
        ast,bst=ar.get('steps') or [],br.get('steps') or []
        names=[c.get('name') or '' for c in ac+bc]+[u for s in ast+bst for u in s.get('uses') or [] if isinstance(u,str)]
        identity=registry.context(names)
        pair={'product':a.get('product',''),'structure':{},'recipe':{'chemicals':[],'steps':[]}}
        for group,fields in [('structure',e.STRUCTURE_FIELDS),('recipe',e.RECIPE_FIELDS)]:
            for field in fields:
                fact=(a.get(group) or {}).get(field);other=(b.get(group) or {}).get(field)
                if idx.problem(field,fact,variant) is None and e.facts_agree(field,fact,other):
                    item={k:fact[k] for k in ('value','unit','quote') if fact.get(k) not in (None,'')}
                    page=idx.support(fact['quote'],variant>=4)['page']
                    if page:item['page']=page
                    pair[group][field]=item
        kept_steps=[];matched_b=set()
        def structural(s,o):
            return e.squash(s.get('action',''))==e.squash(o.get('action','')) or variant>=3 and overlap(s.get('quote',''),o.get('quote',''))>=.5
        def retain_step(s,others,from_b=False):
            quote=s.get('quote') or '';support=idx.support(quote,variant>=4)
            if not support['found']:return None
            possible=[o for o in others if structural(s,o)]
            twin=next((o for o in possible if numeric_steps_agree(s,o)),None)
            single=twin is None
            if single and (variant<5 or possible):return None
            item={'action':s.get('action') or '','description':s.get('description') or '',
                  'quote':quote,'page':support['page'],'uses':[u for u in s.get('uses') or [] if isinstance(u,str)]}
            if single:
                # A one-pass action must not smuggle an unsupported numeric
                # condition back through public prose instead of numeric fields.
                if e.numbers_in(item['description']):item['description']=item['action']
            else:
                if not from_b:matched_b.add(id(twin))
                for key in ('temperature','time'):
                    if s.get(key) is not None and idx.problem('reaction_'+key,e.step_fact(s,key),variant) is None:
                        item[key]=s[key];item[key+'_unit']=s.get(key+'_unit') or ''
            return item
        for s in ast:
            item=retain_step(s,bst)
            if item is not None:kept_steps.append(item)
        if variant>=5:
            for s in bst:
                if id(s) in matched_b or any(structural(s,o) for o in ast):continue
                item=retain_step(s,ast,True)
                if item is None:continue
                pos=idx.support(item['quote'],True)['position']
                before=next((i for i,x in enumerate(kept_steps) if idx.support(x['quote'],True)['position']>pos),len(kept_steps))
                kept_steps.insert(before,item)
        pair['recipe']['steps']=kept_steps
        kept=[];used_b=set()
        def retain_chemical(c,other):
            name=c.get('name') or '';quote=c.get('quote') or '';support=idx.support(quote,variant>=4)
            if not name.strip():return None
            ordinary=other is not None and support['found']
            if not ordinary and variant>=2:
                step=next((s for s in kept_steps if identity.mentioned(name,s['quote'])),None)
                if step is not None:quote=step['quote'];support=idx.support(quote,variant>=4);ordinary=True
            if not ordinary and variant>=5 and support['found'] and identity.mentioned(name,quote):ordinary=True
            if not ordinary:return None
            return {'name':name,'role':c.get('role') or '','quote':quote,'page':support['page'],**chemical_amount(c,other,idx,variant)}
        for c in ac:
            matches=[o for o in bc if identity.same(c.get('name'),o.get('name'))]
            # Same quantity first avoids matching repeated charges to a different
            # reported charge of that chemical; it does not invent quantities.
            other=next((o for o in matches if chemical_amount(c,o,idx,variant)),matches[0] if matches else None)
            item=retain_chemical(c,other)
            if item is None and other is not None:item=retain_chemical(other,c)
            if item is not None:kept.append(item)
            if other is not None:used_b.add(id(other))
        for c in bc:
            if id(c) in used_b:continue
            other=next((o for o in ac if identity.same(c.get('name'),o.get('name'))),None)
            item=retain_chemical(c,other)
            if item is not None and not any(identity.same(item['name'],x['name']) and item.get('amount')==x.get('amount') and item.get('unit')==x.get('unit') for x in kept):kept.append(item)
        if variant>=2:
            for s in kept_steps:
                for name in s['uses']:
                    if any(identity.same(name,c['name']) for c in kept):continue
                    if identity.mentioned(name,s['quote']):
                        # No model-reported chemical supplies a role/amount here.
                        kept.append({'name':name,'role':'','quote':s['quote'],'page':s['page']})
        pair['recipe']['chemicals']=kept;final.append(pair)
    return final
