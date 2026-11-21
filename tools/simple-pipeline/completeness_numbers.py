"""Local Y1 experiment: add numbers to unchanged V5 entities only."""
from bisect import bisect_left
import math
import re
from collections import defaultdict

from completeness_check import check, QuoteIndex, overlap
from completeness_identity import ChemicalIdentity
import mattersyn_simple as e

NUMERIC_FIELDS=('amount','reaction_temperature','reaction_time','size','emission_peak','plqy')
NUMBER=re.compile(r'(?<![\w.])[-+]?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?')
WORDS=re.compile(r'\b('+'|'.join(e.WORDS)+r')\b')


def tokens(clean):
    for m in NUMBER.finditer(clean):
        yield m.start(),m.end(),float(m[0].replace(',',''))
    for m in WORDS.finditer(clean):
        yield m.start(),m.end(),float(e.WORDS[m[0]])


def occurrences(clean,offsets):
    return [(bisect_left(offsets,a),bisect_left(offsets,b),n) for a,b,n in tokens(clean)]


class NumericSupport:
    def __init__(self,text):
        self.idx=QuoteIndex(text)
        self.paper_numbers=occurrences(self.idx.clean,self.idx.offsets)
        self.cache={}

    def locate(self,field,fact):
        if not fact:return None
        val=fact.get('value');quote=fact.get('quote') or '';unit=fact.get('unit') or ''
        if not isinstance(val,(int,float)) or isinstance(val,bool) or not math.isfinite(val) or not unit.strip():
            return None
        x=e.to_canonical(val,unit,field)
        lo,hi=e.LIMITS.get(field,(-math.inf,math.inf))
        if x is None or not math.isfinite(x) or not lo<=x<=hi:return None
        key=(quote,val)
        if key in self.cache:return self.cache[key]
        q=e.letters(quote);hit=None
        if len(q)>=8:
            clean=e.clean(quote).lower()
            qo=[i for i,c in enumerate(clean) if c.isalnum()]
            matches=[(a,b) for a,b,n in occurrences(clean,qo) if e.same_number(val,n,1e-7)]
            if matches:
                pos=self.idx.letters.find(q)
                runs=[]
                if pos>=0:
                    while pos>=0:
                        runs.append((0,pos,len(q)))
                        pos=self.idx.letters.find(q,pos+1)
                else:
                    self.idx.matcher.set_seq1(q)
                    run=self.idx.matcher.find_longest_match()
                    if run.size*10>=9*len(q):runs=[run]
                for a,b,span in runs:
                    if not any(a<=qi<qj<=a+span and any(si==b+qi-a and sj==b+qj-a and
                          e.same_number(val,n,1e-7) for si,sj,n in self.paper_numbers)
                          for qi,qj in matches):continue
                    start=self.idx.offsets[b]
                    markers=list(re.finditer(r'\[page (\d+)\]\n',self.idx.clean[:start]))
                    hit={'quote':quote,'page':int(markers[-1][1]) if markers else None}
                    break
        self.cache[key]=hit
        return hit


def amount_fact(c):
    return {'value':c.get('amount'),'unit':c.get('unit'),'quote':c.get('quote')}


def same(field,a,b):
    if field=='amount' and e.squash(a.get('unit'))!=e.squash(b.get('unit')):return False
    if field in ('emission_peak','plqy') and e.squash(a.get('unit'))!=e.squash(b.get('unit')):return False
    x,y=(e.to_canonical(p.get('value'),p.get('unit'),field) for p in (a,b))
    return x is not None and y is not None and math.isclose(x,y,rel_tol=1e-8,abs_tol=1e-8)


def proposed(field,a,b,support):
    def reported(f):
        return isinstance(f,dict) and f.get('value') not in (None,'','not reported')
    sides=[list(filter(reported,side)) for side in (a,b)]
    all_reported=[f for side in sides for f in side]
    if not all_reported or not all(same(field,all_reported[0],f) for f in all_reported):
        return None
    for fact in all_reported:
        binding=support.locate(field,fact)
        if binding:
            return {'value':fact['value'],'unit':fact['unit'],**binding}
    return None


def identity_for(registry,chemicals,steps):
    return registry.context([c.get('name','') for c in chemicals]+
                           [n for s in steps for n in s.get('uses',[]) if isinstance(n,str)])


def add_number(dst,key,fact):
    if fact:
        dst[key]=fact['value']
        dst['unit' if key=='amount' else key+'_unit']=fact['unit']
        dst[key+'_quote']=fact['quote']
        if fact['page']:dst[key+'_page']=fact['page']


def competing_actions_share_quote(item,sides,exact):
    """An overlap is not a numeric carrier when it names several steps."""
    q=item.get('quote')
    if not q:return False
    return any(not picks and len({e.squash(s.get('action','')) for s in side
                                 if s.get('quote')==q})>1 for side,picks in zip(sides,exact))


def check_v6(text,a,b,registry=None,single_fields=NUMERIC_FIELDS):
    registry=registry or ChemicalIdentity()
    allowed=set(single_fields);assert allowed<=set(NUMERIC_FIELDS)
    base=check(text,a,b,5,registry)
    if not allowed:return base
    matched=[(l,r) for l,r in e.match_pairs(a['pairs'],b['pairs']) if r is not None]
    assert len(matched)==len(base)
    support=NumericSupport(text)
    for (left,right),p in zip(matched,base):
        ar,br=left.get('recipe') or {},right.get('recipe') or {}
        lc,rc=ar.get('chemicals') or [],br.get('chemicals') or []
        ls,rs=ar.get('steps') or [],br.get('steps') or []
        identity=identity_for(registry,lc+rc,ls+rs)
        for key,section in (('size','structure'),('emission_peak','structure'),('plqy','structure'),
                            ('reaction_temperature','recipe'),('reaction_time','recipe')):
            if key not in allowed or p[section].get(key):continue
            f=proposed(key,[(left.get(section) or {}).get(key)],[(right.get(section) or {}).get(key)],support)
            if f:p[section][key]={k:v for k,v in f.items() if v is not None}
        for item in p['recipe']['chemicals']:
            if 'amount' not in allowed or item.get('amount') is not None:continue
            matches=[[c for c in rows if identity.same(item['name'],c.get('name',''))] for rows in (lc,rc)]
            # When one side names several charges, narrow only by the kept
            # quote; without a unique binding the conflict test remains strict.
            for i,rows in enumerate(matches):
                identical=[c for c in rows if c.get('quote')==item.get('quote')]
                if len(identical)==1:matches[i]=identical
            if not any(matches):continue
            add_number(item,'amount',proposed('amount',*[list(map(amount_fact,v)) for v in matches],support))
        for item in p['recipe']['steps']:
            exact=[[s for s in rows if s.get('quote')==item.get('quote') and
                    e.squash(s.get('action',''))==e.squash(item.get('action',''))] for rows in (ls,rs)]
            if sum(map(len,exact))==0:continue
            matches=[same_quote or [s for s in rows if
                      overlap(s.get('quote',''),item.get('quote',''))>=.5 or
                      e.squash(s.get('action',''))==e.squash(item.get('action',''))]
                     for same_quote,rows in zip(exact,(ls,rs))]
            for k in ('temperature','time'):
                f='reaction_'+k
                if f not in allowed or item.get(k) is not None:continue
                fact=proposed(f,*[[e.step_fact(s,k) for s in arr] for arr in matches],support)
                if fact and competing_actions_share_quote(item,(ls,rs),exact):
                    own=[e.step_fact(s,k) for arr in exact for s in arr]
                    if not any(q and same(f,fact,q) for q in own):continue
                add_number(item,k,fact)
    return base
