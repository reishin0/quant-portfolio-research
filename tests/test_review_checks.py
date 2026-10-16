import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from review_checks import (ROOT, PAPER_SHA, JOURNAL_HEAD, require_hash,
                           verify_journal_snapshot, verify_review_snapshot)


class PublicationReviewTests(unittest.TestCase):
    def test_current_frozen_snapshot_passes(self):
        self.assertEqual(verify_review_snapshot()['status'], 'VERIFIED_DATED_SNAPSHOT')

    def test_missing_journal_fails_instead_of_looking_like_no_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'missing, truncated'):
                verify_journal_snapshot(directory)

    def test_terminal_entry_deletion_detected(self):
        with self.assertRaisesRegex(ValueError, 'missing, truncated'):
            verify_journal_snapshot(ROOT/'data/paper_journal_20261016', count=2)

    def test_changed_protocol_binding_detected(self):
        with self.assertRaisesRegex(ValueError, 'protocol binding'):
            verify_journal_snapshot(ROOT/'data/paper_journal_20261016', protocol_sha='0'*64)

    def test_changed_policy_bytes_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'protocol.json'
            path.write_text('{"cost":10}', encoding='utf-8')
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            require_hash(path, expected)
            path.write_text('{"cost":20}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'changed'):
                require_hash(path, expected)

    def test_review_only_adds_integrity_cell_and_anchored_journal_read(self):
        from run_amended_analysis import build_amended_notebook
        from run_reviewed_analysis import build_reviewed_notebook
        prior, _ = build_amended_notebook()
        reviewed, _ = build_reviewed_notebook()
        sources = {c.id: c.source for c in reviewed.cells if c.cell_type == 'code'}
        self.assertEqual(len(sources), 59)
        for cell in prior.cells:
            if cell.cell_type != 'code':
                continue
            expected = cell.source.replace("verify_decision_journal('data/paper_journal_20261016')",
                                           "verify_journal_snapshot('data/paper_journal_20261016')")
            self.assertEqual(sources[cell.id], expected)


if __name__ == '__main__':
    unittest.main()
