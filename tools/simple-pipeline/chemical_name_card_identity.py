"""Stable IDs for printed-name cards, without asserting compound equivalence.

The historical slug is retained when unused or bound to the exact printed name.
A distinct printed name gets a deterministic suffix instead of inheriting an
unrelated existing card. This changes no molecular identity or old binding.
"""
import hashlib
import re
import unicodedata


def literal_name(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(value))).strip()


def name_card_id(name, entries, slug):
    printed = literal_name(name)
    if not printed:
        raise ValueError('A name card needs a nonempty printed name')
    base = 'name-card-' + slug(name, 60)
    known = {entry['id']: entry for entry in entries}
    if len(known) != len(entries):
        raise ValueError('Duplicate chemical registry IDs')
    def available(identifier):
        existing = known.get(identifier)
        return existing is None or literal_name(existing['name']) == printed
    if available(base):
        return base
    suffix = hashlib.sha256(printed.encode('utf-8')).hexdigest()
    for length in (12, 24, 64):
        identifier = base + '-' + suffix[:length]
        if available(identifier):
            return identifier
    raise ValueError('Printed-name card identity collision')
