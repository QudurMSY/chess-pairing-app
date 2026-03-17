
import unittest
from src.core.player_manager import PlayerManager
from src.database.database import Database

import os

class TestPlayerImport(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.player_manager = PlayerManager(self.db)
        self.test_file = "test_import_file.txt"

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_trial_tournament_file_import(self):
        result = self.player_manager.import_players_from_file("trial_tournament.txt")
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 18)
        self.assertEqual(len(result['players']), 18)
        self.assertEqual(result['players'][0]['name'], "Pedram Rahmani")
        self.assertEqual(result['players'][0]['elo'], 2045)
        self.assertEqual(result['players'][2]['name'], "Mohammad Ali Kolivand")
        self.assertEqual(result['players'][2]['elo'], 1968)
        self.assertEqual(result['players'][17]['name'], "Radin Eidi")
        self.assertEqual(result['players'][17]['elo'], 0)

    def test_file_not_found(self):
        result = self.player_manager.import_players_from_file("non_existent_file.txt")
        self.assertFalse(result['success'])
        self.assertIn("File not found", result['errors'][0])

    def test_import_with_federation(self):
        with open(self.test_file, "w") as f:
            f.write("Magnus Carlsen NOR\n")
            f.write("Hikaru Nakamura USA\n")
        result = self.player_manager.import_players_from_file(self.test_file)
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(result['players'][0]['federation'], "NOR")
        self.assertEqual(result['players'][1]['federation'], "USA")

    def test_import_with_fide_id(self):
        with open(self.test_file, "w") as f:
            f.write("Fabiano Caruana 1234567\n")
        result = self.player_manager.import_players_from_file(self.test_file)
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['players'][0]['fide_id'], "1234567")

    def test_import_with_elo(self):
        with open(self.test_file, "w") as f:
            f.write("Ian Nepomniachtchi 2770\n")
        result = self.player_manager.import_players_from_file(self.test_file)
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['players'][0]['elo'], 2770)

    def test_import_invalid_lines(self):
        with open(self.test_file, "w") as f:
            f.write("Invalid Line\n")
            f.write("Another Invalid Line\n")
        result = self.player_manager.import_players_from_file(self.test_file)
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)

    def test_import_missing_name(self):
        with open(self.test_file, "w") as f:
            f.write("Anish 2700\n")
            f.write("Giri 2700\n")
        result = self.player_manager.import_players_from_file(self.test_file)
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 0)

    def test_import_mixed_valid_and_invalid(self):
        with open(self.test_file, "w") as f:
            f.write("Valid Player 2600\n")
            f.write("Invalid Line\n")
            f.write("Another Valid 2500\n")
        result = self.player_manager.import_players_from_file(self.test_file)
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(result['players'][0]['name'], "Valid Player")
        self.assertEqual(result['players'][1]['name'], "Another Valid")


if __name__ == '__main__':
    unittest.main()
