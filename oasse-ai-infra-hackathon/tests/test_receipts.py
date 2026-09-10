import unittest

from oasse_physical_ai.receipts import ReceiptChain


class ReceiptTests(unittest.TestCase):
    def test_chain_verifies(self):
        c = ReceiptChain()
        c.seal("A", {"x": 1})
        c.seal("B", {"y": 2})
        self.assertTrue(c.verify())

    def test_chains_to_previous(self):
        c = ReceiptChain()
        a = c.seal("A", {"x": 1})
        b = c.seal("B", {"y": 2})
        self.assertEqual(b.prev_hash, a.receipt_hash)

    def test_tamper_detected(self):
        c = ReceiptChain()
        c.seal("A", {"x": 1})
        c._receipts[0].payload["x"] = 9
        self.assertFalse(c.verify())


if __name__ == "__main__":
    unittest.main()
