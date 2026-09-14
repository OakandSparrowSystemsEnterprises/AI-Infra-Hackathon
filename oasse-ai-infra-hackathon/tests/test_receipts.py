import unittest
from dataclasses import replace

from oasse_physical_ai.receipts import ReceiptChain


class ReceiptTests(unittest.TestCase):
    def test_chain_verifies(self):
        c = ReceiptChain()
        c.seal("A", {"x": 1})
        c.seal("B", {"y": 2})
        self.assertTrue(c.verify())
        self.assertTrue(c.assert_intact())

    def test_chains_to_previous(self):
        c = ReceiptChain()
        a = c.seal("A", {"x": 1})
        b = c.seal("B", {"y": 2})
        self.assertEqual(b.prev_hash, a.receipt_hash)

    def test_public_receipts_are_detached_snapshots(self):
        c = ReceiptChain()
        sealed = c.seal("A", {"x": 1})
        sealed.payload["x"] = 7
        exported = c.all()
        exported[0].payload["x"] = 9
        self.assertEqual(c.all()[0].payload["x"], 1)
        self.assertTrue(c.assert_intact())
        self.assertTrue(c.verify())

    def test_private_payload_corruption_is_detected_by_full_verifier(self):
        c = ReceiptChain()
        c.seal("A", {"x": 1})
        stored = c._receipts[0]
        c._receipts[0] = replace(stored, payload_json=b'{"x":9}')
        self.assertFalse(c.verify())
        self.assertFalse(c.assert_intact())

    def test_receipt_identity_is_hash_bound(self):
        c = ReceiptChain()
        c.seal("A", {"x": 1})
        stored = c._receipts[0]
        c._receipts[0] = replace(stored, receipt_id="rcpt-forged")
        self.assertFalse(c.verify())


if __name__ == "__main__":
    unittest.main()
