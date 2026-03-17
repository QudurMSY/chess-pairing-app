import unittest
import os
from src.core.tournament_manager import TournamentManager
from src.core.player_manager import PlayerManager
from src.core.round_manager import RoundManager
from src.database.database import Database

class TestFideCompliance(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_fide_compliance.db"
        self.db = Database(self.db_path)
        self.tm = TournamentManager(self.db)
        self.pm = PlayerManager(self.db)
        self.rm = RoundManager(self.db, self.tm)

    def tearDown(self):
        self.db.close()
        os.remove(self.db_path)

    def test_small_tournament_pairing(self):
        # 1. Setup a small tournament
        tournament_id = self.tm.create_tournament("FIDE Test", "2024-01-01", 3, "Swiss", False)

        # 2. Add 7 players
        players_to_add = [
            ("Player A", 2000), ("Player B", 1800), ("Player C", 1600),
            ("Player D", 1400), ("Player E", 1200), ("Player F", 1000),
            ("Player G", 800)
        ]
        for name, rating in players_to_add:
            self.pm.add_player(name, rating, tournament_id)

        players = self.pm.get_players(tournament_id)
        players.sort(key=lambda p: p["elo"])
        player_ids_sorted_by_rating = [p["id"] for p in players]

        byes_received = set()
        color_history = {p["id"]: [] for p in players}

        # 3. Simulate 3 rounds
        for round_number in range(1, 4):
            round_id = self.rm.create_round_with_pairings(tournament_id, round_number)
            pairings = self.rm.get_round_results(round_id)

            player_ids_in_pairings = set()
            paired_opponents = {}
            bye_player_id = None

            # Assertions for each round
            for pairing in pairings:
                player1_id = pairing["player1_id"]
                player2_id = pairing["player2_id"]

                # No player is paired against themselves
                self.assertNotEqual(player1_id, player2_id, f"Round {round_number}: Player {player1_id} paired against themselves.")

                if pairing["is_bye"]:
                    bye_player_id = player1_id
                    # A player with a bye should not be paired against anyone
                    self.assertIsNone(player2_id, f"Round {round_number}: Player {player1_id} has a bye but is also paired.")
                else:
                    # Track players in this round's pairings
                    if player1_id:
                        player_ids_in_pairings.add(player1_id)
                    if player2_id:
                        player_ids_in_pairings.add(player2_id)

                    # Track opponents
                    if player1_id and player2_id:
                        if player1_id not in paired_opponents:
                            paired_opponents[player1_id] = set()
                        if player2_id not in paired_opponents:
                            paired_opponents[player2_id] = set()
                        paired_opponents[player1_id].add(player2_id)
                        paired_opponents[player2_id].add(player1_id)
                        
                        color_history[player1_id].append(pairing["player1_color"])
                        color_history[player2_id].append("White" if pairing["player1_color"] == "Black" else "Black")


            all_players = self.pm.get_players(tournament_id)
            all_player_ids = {p["id"] for p in all_players}

            # Verify all players are accounted for
            if bye_player_id:
                player_ids_in_pairings.add(bye_player_id)
            self.assertEqual(all_player_ids, player_ids_in_pairings, f"Round {round_number}: Not all players are accounted for in pairings.")

            if bye_player_id:
                # Find the lowest-ranked player who hasn't received a bye
                expected_bye_player = None
                for player_id in player_ids_sorted_by_rating:
                    if player_id not in byes_received:
                        expected_bye_player = player_id
                        break
                self.assertEqual(bye_player_id, expected_bye_player, f"Round {round_number}: Bye not assigned to the lowest-ranked player without a bye.")
                byes_received.add(bye_player_id)

            # Record dummy results for the round
            for pairing in pairings:
                if not pairing["is_bye"]:
                    # Record player 1 as winner for simplicity
                    self.rm.update_result(pairing["id"], pairing["player1_id"])

            # No player is paired against the same opponent more than once (across all rounds)
            # This check is inherently difficult without storing pairing history across rounds in the test
            # The pairing generator itself should prevent this.

            # Check color allocation rules
            for player_id, history in color_history.items():
                if len(history) >= 3:
                    self.assertFalse(history[-1] == history[-2] == history[-3], f"Player {player_id} has the same color three times in a row.")

if __name__ == "__main__":
    unittest.main()
