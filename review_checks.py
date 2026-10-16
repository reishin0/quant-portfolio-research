"""Read-only publication checks; never rewrite either frozen research protocol."""
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

from forward_evaluation import verify_protocol
from portfolio_amendments import verify_decision_journal

ROOT = Path(__file__).resolve().parent
BASELINE_SHA = 'a1924728765f10d91d7620054e5d2e604e1b3df3f47b872c74fefce41c85d244'
PARENT_SHA = '97226bad70fc261537536322b6450d36379c8a389b99bd52642f58a3cea59bf2'
PAPER_SHA = '6cad006a15f77ffd19fa5147e3262f1693b8edf68f13a20de980e8653a05a536'
JOURNAL_HEAD = '5808c1f3bcfb7c85202cd42ab552675f6605f3d2c4d9a1bb0d27b80a16cfdc66'


def require_hash(path, expected):
    path = Path(path)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f'Review snapshot missing or changed: {path.name}')


def verify_journal_snapshot(directory, protocol_sha=PAPER_SHA, head=JOURNAL_HEAD, count=1):
    """Bind the complete dated snapshot to a retained head, detecting tail deletion.

    A later journal requires its own review receipt, not a replacement anchor here.
    Git supplies retained history; this is not an external notarization service.
    """
    entries = verify_decision_journal(directory)
    if len(entries) != count or not entries or entries[-1]['sha256'] != head:
        raise ValueError('Journal snapshot missing, truncated or changed.')
    if any(entry.get('protocol_sha256') != protocol_sha for entry in entries):
        raise ValueError('Journal protocol binding changed.')
    return entries


def verify_review_snapshot(root=ROOT):
    root = Path(root)
    require_hash(root/'portfolio_construction.ipynb', BASELINE_SHA)
    require_hash(root/'data/forward_protocol_20261009.json', PARENT_SHA)
    require_hash(root/'research/paper_protocol_20261016.json', PAPER_SHA)
    verify_protocol(root/'data/forward_protocol_20261009.json', root=root)
    paper = json.loads((root/'research/paper_protocol_20261016.json').read_text(encoding='utf-8'))
    require_hash(root/paper['parent_protocol'], paper['parent_protocol_sha256'])
    for name, expected in paper['file_sha256'].items():
        require_hash(root/name, expected)
    for name, expected in paper['packages'].items():
        if version(name) != expected:
            raise ValueError(f'Amended runtime changed: {name}')
    manifest = json.loads((root/'data/refresh_20261016/refresh_manifest.json').read_text(encoding='utf-8'))
    optional_raw = {'gld_historical.xlsx', 'ff5_source.zip', 'yahoo_daily_raw.csv'}
    for name, expected in manifest['files'].items():
        path = root/'data/refresh_20261016'/name
        if name in optional_raw and not path.exists():
            continue
        require_hash(path, expected)
    original = json.loads((root/'data/manifest.json').read_text(encoding='utf-8'))
    for entry in original['files']:
        require_hash(root/entry['path'], entry['original_sha256'])
    entries = verify_journal_snapshot(root/'data/paper_journal_20261016')
    return {'baseline_sha256': BASELINE_SHA, 'parent_protocol_sha256': PARENT_SHA,
            'paper_protocol_sha256': PAPER_SHA, 'journal_head_sha256': entries[-1]['sha256'],
            'journal_entries': len(entries), 'status': 'VERIFIED_DATED_SNAPSHOT'}
