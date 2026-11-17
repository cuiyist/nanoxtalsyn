"""Calibrated V1 identity matching, local registry only. No model or network.

This identifies reported chemical labels; it does not assign reference geometry,
salt components, hydration, an isomer, or a material role. Formula agreement
alone never equates two named compounds. Ambiguous registry names stay unresolved.
"""
import collections
import json
from pathlib import Path
import re
import sys
import unicodedata

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'recipe-atlas/scripts'))
from chemical_L_identity import clean_name
from chemical_reference_identity import FIXED_NAMES, STANDARD_ABBREVIATION_IDENTITIES, material_context_reason, identity
from formula_equivalence import parse_formula


def norm(value):
    value=unicodedata.normalize('NFKC',str(value or '')).strip(' .,;')
    return re.sub(r'\s*([()])\s*',r'\1',re.sub(r'\s+',' ',value)).casefold()


def formula(value):
    value=unicodedata.normalize('NFKC',str(value or '')).strip()
    return parse_formula(value)


def explicit_parts(value):
    """Only a terminal complete name (abbreviation/formula); not oxidation/stereo."""
    match=re.fullmatch(r'(.+)\s+\((.{1,80})\)',str(value or '').strip())
    if not match:return None
    long,short=match.groups()
    if short in {'I','II','III','IV','V','VI','VII','VIII','R','S','E','Z'}:return None
    if not (re.fullmatch(r'[A-Z][A-Za-z0-9-]{1,15}',short) or formula(short)):return None
    return long,short


class ChemicalIdentity:
    def __init__(self,entries=None):
        if entries is None:
            entries=json.loads((REPO/'recipe-atlas/static/assets/chemical-registry/registry.json').read_text())['entries']
        self.names=collections.defaultdict(set);self.formulas=collections.defaultdict(set)
        self.aliases=collections.defaultdict(set);self.ids={e['id']:e for e in entries}
        token_formulas=collections.defaultdict(set);definitions=[]
        for e in entries:
            if material_context_reason(e) is not None or e.get('depictionKind') in {'mixture','polymer','equipment','support'}:continue
            token=identity(e)
            aliases={e.get('name',''),*e.get('aliases',[])}-{''}
            # A short unqualified compound-registry identifier is itself a
            # supported lookup label (for example the registry's topse entry).
            if e.get('pubchemCid') and re.fullmatch(r'[a-z]{2,12}',e['id']):aliases.add(e['id'])
            for name in aliases:
                self.names[norm(name)].add(token)
                cleaned,_=clean_name(name)
                if cleaned:self.names[norm(cleaned)].add(token)
                self.aliases[token].add(name)
                if explicit_parts(name):definitions.append((token,explicit_parts(name)))
            # Registry formula can bind a literal formula to its already named
            # compound only when the formula has one unique compound identity.
            f=formula(e.get('formula'))
            if f is not None:
                self.formulas[f].add(token);self.aliases[token].add(e['formula'])
                token_formulas[token].add(f)
        # Several source-local registry rows may describe the same named
        # compound. They are not different identities solely for lacking a CID.
        # Collapse only exact full names with no CID/connectivity/formula conflict;
        # never collapse two named compounds just because their formulas agree.
        parent={t:t for t in self.aliases}
        def root(t):
            while parent[t]!=t:parent[t]=parent[parent[t]];t=parent[t]
            return t
        def unite(tokens):
            roots={root(t) for t in tokens}
            members={t for t in parent if root(t) in roots}
            cids={t for t in members if t[0]=='CID'};smiles={t for t in members if t[0]=='smiles'}
            forms=set().union(*(token_formulas[t] for t in members)) if members else set()
            if len(cids)>1 or len(smiles)>1 or len(forms)>1:return
            chosen=next(iter(cids or smiles),min(roots,key=str))
            for t in roots:parent[t]=chosen
        for name,tokens in self.names.items():
            if len(tokens)>1 and formula(name) is None:unite(tokens)
        for token,(long,short) in definitions:
            hits=self.names.get(norm(long),set())
            if hits:
                unite({token,*hits,*self.names.get(norm(short),set())})
                # A contradictory token keeps separate roots and therefore an
                # ambiguous lookup, rather than being silently overwritten.
                self.names[norm(short)].update({token,*hits})
        for key,values in self.names.items():self.names[key]={root(t) for t in values}
        for key,values in self.formulas.items():self.formulas[key]={root(t) for t in values}
        merged=collections.defaultdict(set)
        for token,aliases in self.aliases.items():merged[root(token)].update(aliases)
        self.aliases=merged
        for alias,eid in FIXED_NAMES.items():
            if eid in self.ids:
                token=identity(self.ids[eid]);self.names[norm(alias)]={token};self.aliases[token].add(alias)
        for alias,proof in STANDARD_ABBREVIATION_IDENTITIES.items():
            token=('CID',proof['cid'])
            for name in (alias,proof['name']):self.names[norm(name)]={token};self.aliases[token].add(name)
            f=formula(proof['formula']);self.formulas[f].add(token);self.aliases[token].add(proof['formula'])

    def tokens(self,name):
        f=formula(name)
        if f is not None:
            hits=self.formulas.get(f,set())
            resolved={t for t in hits if t[0] in {'CID','smiles'} or
                      t[0]=='entry' and not re.search(r'(?:19|20)\d\d|^name-card-',t[1])}
            if resolved:hits=resolved
            return set(hits) if len(hits)==1 else set()
        cleaned,_=clean_name(name)
        hits=self.names.get(norm(name)) or self.names.get(norm(cleaned)) or set()
        return set(hits) if len(hits)==1 else set()

    def context(self,names):return Context(self,names)


class Context:
    def __init__(self,registry,names):
        self.registry=registry;self.explicit=collections.defaultdict(set)
        for value in names:
            parts=explicit_parts(value)
            if not parts:continue
            long,short=parts
            a,b=registry.tokens(long),registry.tokens(short)
            if a and b and not a&b:continue
            token=next(iter(a or b),('explicit',norm(long)))
            for name in (value,long,short):self.explicit[norm(name)].add(token)

    def tokens(self,name):
        values=self.explicit.get(norm(name),set())
        return set(values) if len(values)==1 else self.registry.tokens(name) if not values else set()

    def same(self,left,right):
        lf,rf=formula(left),formula(right)
        if lf is not None and rf is not None:return lf==rf
        # A formula cannot fall through a casefold label comparison (CO != Co).
        if lf is None and rf is None:
            a,_=clean_name(left);b,_=clean_name(right)
            if norm(a) and norm(a)==norm(b):return True
        return bool(self.tokens(left)&self.tokens(right))

    def spellings(self,name):
        result={str(name)}
        cleaned,_=clean_name(name)
        if cleaned:result.add(cleaned)
        tokens=self.tokens(name)
        for token in tokens:
            for alias in self.registry.aliases.get(token,set()):
                # Do not use a formula shared by several compounds as a name's
                # mention alias. Avoid ambiguous registry aliases as well.
                if self.same(name,alias):result.add(alias)
        for key,values in self.explicit.items():
            if len(values)==1 and values&tokens:result.add(key)
        return result

    def mentioned(self,name,text):
        text=unicodedata.normalize('NFKC',str(text or ''))
        for label in self.spellings(name):
            if not label.strip():continue
            bits=re.split(r'\s+',unicodedata.normalize('NFKC',label).strip())
            pattern=r'(?<!\w)'+r'\s+'.join(re.escape(x) for x in bits)+r'(?!\w)'
            flags=0 if formula(label) is not None else re.I
            if re.search(pattern,text,flags):return True
        return False
