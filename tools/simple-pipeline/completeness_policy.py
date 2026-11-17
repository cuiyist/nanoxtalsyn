"""Explicit owner-calibrated CHECK admission, separate from scientific audit.

Legacy documents retain their exact legacy marker. Calibrated documents must
bind the checked-in decision; a variant cannot masquerade as unanimous legacy
two-pass agreement. No paper field can select a different policy or optics gate.
"""
import json
from pathlib import Path
import re

LEGACY_CHECK='two passes agree, quotes found'
CALIBRATED_CHECK='owner-calibrated two-pass CHECK; source-quote support'
POLICY_PATH=Path(__file__).with_name('completeness_policy.json')


def load_policy():
    policy=json.loads(POLICY_PATH.read_text(encoding='utf-8'))
    assert policy['schema_version']==1
    assert policy['program']=='owner-20261116-completeness'
    assert type(policy['adopted_check_variant']) is int and policy['adopted_check_variant'] in range(6)
    assert re.fullmatch(r'[0-9a-f]{64}',policy['decision_sha256'])
    assert set(policy['optical_fields'])<= {'absorption_peak','emission_peak','plqy'}
    admitted=set()
    for field,counts in policy['optical_gates'].items():
        assert type(counts['correct']) is int and type(counts['total']) is int
        assert 0<=counts['correct']<=counts['total']
        passing=counts['total']>0 and counts['correct']/counts['total']>=.95
        assert counts['convert'] is passing
        if passing:admitted.add(field)
    assert set(policy['optical_fields'])==admitted
    return policy


def binding(policy=None):
    policy=policy or load_policy()
    return {'program':policy['program'],'variant':policy['adopted_check_variant'],
            'decision_sha256':policy['decision_sha256']}


def is_checked_document(doc):
    if not isinstance(doc,dict):return False
    if doc.get('check')==LEGACY_CHECK:return 'check_policy' not in doc
    return doc.get('check')==CALIBRATED_CHECK and doc.get('check_policy')==binding()


def calibrated_policy(doc):
    """Return the bound policy or None for legacy/pure-conversion fixtures."""
    if doc.get('check')!=CALIBRATED_CHECK:
        if 'check_policy' in doc:raise ValueError('Calibrated policy requires its truthful CHECK marker')
        return None
    if not is_checked_document(doc):raise ValueError('Calibrated CHECK decision binding failed')
    return load_policy()
