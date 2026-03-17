import unittest
import os
from src.database.database import Database
from src.core.tournament_manager import TournamentManager
from src.core.player_manager import PlayerManager
from src.core.pairing.pairing_generator import PairingGenerator

class TestWithdrawal(unittest.TestCase):

    def setUp(self):
        """Set up a temporary database and test data for each test."""
        self.db_path = "test_withdrawal.db"
        self.db = Database(self.db_path)
        self.tm = TournamentManager(self.db)
        self.pm = PlayerManager(self.db)
        self.pg = PairingGenerator(self.db)

        # Create a test tournament
        self.tournament_id = self.tm.create_tournament(
            name="Withdrawal Test Tournament",
            start_date="2024-01-01",
            number_of_rounds=4,
            pairing_system="Swiss System",
            is_team_tournament=False
        )

        # Add players
        self.p1_id = self.pm.add_player(name="Player 1", elo=1200, tournament_id=self.tournament_id)
        self.p2_id = self.pm.add_player(name="Player 2", elo=1300, tournament_id=self.tournament_id)
        self.p3_id = self.pm.add_player(name="Player 3", elo=1400, tournament_id=self.tournament_id)
        self.p4_id = self.pm.add_player(name="Player 4", elo=1500, tournament_id=self.tournament_id)

    def tearDown(self):
        """Clean up the database file after each test."""
        self.db.close()
        os.remove(self.db_path)

    def test_withdrawn_player_is_excluded_from_pairings(self):
        """
        Verify that a withdrawn player is not included in the generated pairings.
        """
        # Withdraw Player 3
        self.pm.withdraw_player(self.p3_id)

        # Generate pairings for round 1
        pairings = self.pg.generate_pairings(
            tournament_id=self.tournament_id,
            round_number=1,
            pairing_system="Swiss System"
        )

        # Check that the withdrawn player is not in any of the pairings
        withdrawn_player_in_pairings = False
        for pair in pairings:
            if pair.get("player1_id") == self.p3_id or pair.get("player2_id") == self.p3_id:
                withdrawn_player_in_pairings = True
                break

        self.assertFalse(withdrawn_player_in_pairings, "Withdrawn player should not be in pairings.")

        # Also check that the number of players in pairings is correct
        # There should be one pair and one bye
        
        # There is no bye for 2 players, so this will be one pair. 3 active players - p4 has a bye.
        
        active_players = [self.p1_id, self.p2_id, self.p4_id]
        
        paired_players = set()
        for pair in pairings:
            if not pair.get("is_bye"):
                paired_players.add(pair["player1_id"])
                paired_players.add(pair["player2_id"])

        self.assertEqual(len(paired_players), 2, "There should be one pair of players.")

        # check that bye player is one of the active players
        bye_player_found = False
        for pair in pairings:
            if pair.get("is_bye"):
                self.assertIn(pair.get("player1_id"), active_players, "Bye player should be an active player.")
                bye_player_found = True

        self.assertTrue(bye_player_found, "There should be one bye player.")


if __name__ == '__main__':
    unittest.main()
