import unittest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.pairing.berger_table import BergerTable

class TestBergerTable(unittest.TestCase):
    def test_berger_4_players(self):
        bt = BergerTable()
        pairings = bt.generate_pairings([1, 2, 3, 4])
        
        # Expect 3 rounds
        self.assertEqual(len(pairings), 3)
        
        # Round 1
        r1 = pairings[0]
        # Expect 2 pairs
        self.assertEqual(len(r1), 2)
        # Check for self-pairing (bug regression)
        for p1, p2 in r1:
            self.assertNotEqual(p1, p2, f"Self pairing detected in Round 1: {p1} vs {p2}")
            
    def test_berger_10_players(self):
        bt = BergerTable()
        players = list(range(1, 11))
        pairings = bt.generate_pairings(players)
        
        # Expect 9 rounds
        self.assertEqual(len(pairings), 9)
        
        # Round 1
        r1 = pairings[0]
        self.assertEqual(len(r1), 5)
        for p1, p2 in r1:
             self.assertNotEqual(p1, p2)
             
        # Check standard pairing 1-10
        self.assertIn((1, 10), r1)
        # Check 2-9? (My implementation gives 2-9 with the fix)
        self.assertIn((2, 9), r1)

if __name__ == '__main__':
    unittest.main()
