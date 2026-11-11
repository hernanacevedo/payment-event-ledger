import tempfile
import unittest
from pathlib import Path
from ledger import Ledger, ConflictError, ValidationError

def event(**changes):
    result = dict(tenant="shop", provider="bank", event_id="e1", payment_id="p1", kind="capture", amount=1000, currency="ARS")
    result.update(changes)
    return result

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "journal.db")
        self.ledger = Ledger(self.path)

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def test_duplicate_is_idempotent(self):
        self.assertEqual(self.ledger.ingest([event(), event()]), {"inserted": 1, "duplicates": 1})
        self.assertEqual(len(self.ledger.events("shop")), 1)

    def test_conflict_rolls_back_whole_batch(self):
        self.ledger.ingest([event()])
        with self.assertRaises(ConflictError):
            self.ledger.ingest([event(event_id="fresh"), event(amount=2)])
        self.assertEqual(len(self.ledger.events("shop")), 1)
        self.assertEqual(len(self.ledger.history()), 1)

    def test_identity_is_provider_and_tenant_scoped(self):
        self.ledger.ingest([event(), event(provider="other"), event(tenant="else")])
        self.assertEqual(self.ledger.counts("shop")["capture"], 2)

    def test_parent_may_arrive_later(self):
        self.ledger.ingest([event(event_id="refund", kind="refund", parent_id="e1", amount=100)])
        self.assertEqual(self.ledger.counts("shop")["refund"], 1)

    def test_invalid_batch_leaves_no_events(self):
        with self.assertRaises(ValidationError):
            self.ledger.ingest([event(), event(event_id="bad", amount=True)])
        self.assertEqual(self.ledger.events("shop"), [])
        self.assertEqual(self.ledger.history(), [])

    def test_data_survives_reopen(self):
        self.ledger.ingest([event()])
        self.ledger.close()
        self.ledger = Ledger(self.path)
        self.assertEqual(self.ledger.counts("shop"), {"capture": 1, "refund": 0, "reverse": 0})

    def test_unknown_fields_rejected(self):
        with self.assertRaises(ValidationError):
            self.ledger.ingest([event(secret="not allowed")])

    def test_refund_requires_parent(self):
        with self.assertRaises(ValidationError):
            self.ledger.ingest([event(kind="refund")])

    def test_capture_rejects_parent(self):
        with self.assertRaises(ValidationError):
            self.ledger.ingest([event(parent_id="other")])

    def test_currency_is_exact(self):
        with self.assertRaises(ValidationError):
            self.ledger.ingest([event(currency="ars")])

    def test_positive_minor_units_only(self):
        for value in (0, -1, 2.5, 10**12 + 1):
            with self.assertRaises(ValidationError):
                self.ledger.ingest([event(amount=value)])

    def test_audit_records_duplicate_batches(self):
        self.ledger.ingest([event()])
        self.ledger.ingest([event()])
        self.assertEqual(self.ledger.history()[-1], {"batch_id": 2, "inserted": 0, "duplicates": 1})

if __name__ == "__main__":
    unittest.main()
