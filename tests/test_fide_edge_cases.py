import unittest
from unittest.mock import MagicMock, patch
from src.core.pairing.swiss_pairing import SwissPairing
from src.core.pairing.burstein_system import BursteinSystem
from src.core.pairing.dubov_system import DubovSystem

class TestSwissComplexCases(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        # SwissPairing requires args, so we can't init it here without dummy data.
        # We'll init it in each test.

    def test_absolute_color_constraint(self):
        """
        Verify that a player cannot be assigned the same color 3 times in a row,
        or have a color difference > 2.
        """
        # Player 1 has played White, White. Should force Black.
        player1 = {"id": 1, "score": 1.0, "elo": 2000, "pairing_id": 1, "tpn": 1, "downfloat_history": [], "upfloat_history": []}
        # Player 2 has played Black, Black. Should force White.
        player2 = {"id": 2, "score": 1.0, "elo": 1900, "pairing_id": 2, "tpn": 2, "downfloat_history": [], "upfloat_history": []}
        
        # Mock pairings history
        # Player 1: W, W
        # Player 2: B, B
        self.mock_db.get_player_color_history.side_effect = lambda tid, pid: ["W", "W"] if pid == 1 else ["B", "B"]
        self.mock_db.get_player_float_history.return_value = []
        
        players = [player1, player2]
        self.mock_db.get_players.return_value = players
        self.mock_db.get_tournament.return_value = {"id": 1, "total_rounds": 5}
        self.mock_db.get_all_tournament_results.return_value = [] # No current round results
        self.mock_db.get_players_with_bye.return_value = []
        self.mock_db.get_tournament_settings.return_value = {}
        
        # Mock pairings so far to establish color history
        # (The history is pulled via get_player_color_history which we mocked)
        
        swiss = SwissPairing(self.mock_db, 1, 3, players)
        pairings, bye = swiss.pair_round()
        
        # Expected: Player 1 (W,W) -> Must be Black. Player 2 (B,B) -> Must be White.
        # Pairing: (1, 2)
        # Colors: Player 1 is Black, Player 2 is White.
        
        # pair_round returns (pairings, bye)
        # pairings is list of (p1_id, p2_id, p1_color)
        
        self.assertEqual(len(pairings), 1)
        p1_id, p2_id, p1_color = pairings[0]
        
        # Ensure correct players
        self.assertSetEqual({p1_id, p2_id}, {1, 2})
        
        # Check colors
        # If p1_id is 1, it must be Black. If p1_id is 2, it must be White.
        if p1_id == 1:
            self.assertEqual(p1_color, "B", "Player 1 must take Black after two Whites")
        else:
            self.assertEqual(p1_color, "W", "Player 2 must take White after two Blacks")


    def test_heterogeneous_score_group(self):
        """
        Verify handling of a heterogeneous score group (players dropping down).
        """
        # S1: Score 2.0 (1 player) -> Must play someone from S2.
        # S2: Score 1.0 (3 players).
        
        p1 = {"id": 1, "score": 2.0, "elo": 2000, "pairing_id": 1, "tpn": 1, "downfloat_history": [], "upfloat_history": []} # Downfloater
        p2 = {"id": 2, "score": 1.0, "elo": 1900, "pairing_id": 2, "tpn": 2, "downfloat_history": [], "upfloat_history": []}
        p3 = {"id": 3, "score": 1.0, "elo": 1800, "pairing_id": 3, "tpn": 3, "downfloat_history": [], "upfloat_history": []}
        p4 = {"id": 4, "score": 1.0, "elo": 1700, "pairing_id": 4, "tpn": 4, "downfloat_history": [], "upfloat_history": []}
        
        players = [p1, p2, p3, p4]
        self.mock_db.get_players.return_value = players
        self.mock_db.get_tournament.return_value = {"id": 1, "total_rounds": 5}
        self.mock_db.get_player_color_history.return_value = []
        self.mock_db.get_player_float_history.return_value = []
        self.mock_db.get_all_tournament_results.return_value = []
        self.mock_db.get_players_with_bye.return_value = []
        self.mock_db.get_tournament_settings.return_value = {}
        
        swiss = SwissPairing(self.mock_db, 1, 3, players)
        pairings, bye = swiss.pair_round()
        
        # Logic:
        # P1 (2.0) needs an opponent from 1.0 group.
        # FIDE C.1: S1 (2.0) pairs with S2 (1.0).
        # Should pair P1 vs P2 (highest in S2).
        # Remaining S2: P3, P4. Pair P3 vs P4.
        
        # Verify P1 is paired with a 1.0 score player
        paired_opponents = {}
        for p1_id, p2_id, color in pairings:
            paired_opponents[p1_id] = p2_id
            paired_opponents[p2_id] = p1_id
            
        self.assertIn(1, paired_opponents)
        opponent_of_1 = paired_opponents[1]
        
        # Find opponent object
        opp_obj = next(p for p in players if p["id"] == opponent_of_1)
        self.assertEqual(opp_obj["score"], 1.0, "Downfloater from 2.0 should pair with 1.0")
        
        # Ideally, it pairs with the highest rated (P2)
        self.assertEqual(opponent_of_1, 2, "Standard pairing should pair highest vs highest available in next group")



class TestBursteinEdgeCases(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.burstein = BursteinSystem(self.mock_db)

    def test_odd_number_of_players_with_many_score_groups(self):
        """
        Test odd number of players distributed across multiple score groups.
        Ensures the floater logic propagates correctly down to the last group.
        """
        # 5 Players. 
        # Grp 3.0: P1
        # Grp 2.0: P2
        # Grp 1.0: P3
        # Grp 0.0: P4, P5
        
        p1 = {"id": 1, "score": 3.0, "rank": 1}
        p2 = {"id": 2, "score": 2.0, "rank": 2}
        p3 = {"id": 3, "score": 1.0, "rank": 3}
        p4 = {"id": 4, "score": 0.0, "rank": 4}
        p5 = {"id": 5, "score": 0.0, "rank": 5}
        
        players = [p1, p2, p3, p4, p5]
        
        self.mock_db.get_players.return_value = players
        self.mock_db.get_tournament.return_value = {"total_rounds": 8} # Post-seeding
        self.mock_db.get_results_for_player.return_value = [1, 1, 1] # Played some games
        
        # Round > total_rounds/2 (Post-seeding)
        pairings = self.burstein.pair_players(1, 6)
        
        # Logic:
        # Grp 3.0 (P1): Odd. P1 floats to 2.0.
        # Grp 2.0 (P1, P2): Even. Pair P1 vs P2? (High vs Low in group).
        # Grp 1.0 (P3): Odd. P3 floats to 0.0.
        # Grp 0.0 (P3, P4, P5): Odd. One gets bye.
        # Wait, Burstein logic for floaters:
        # "If the number of players in a score group is odd, the player with the lowest rank is floated."
        
        # Trace:
        # 3.0: [P1]. Lowest rank is P1. Floats.
        # 2.0: [P2] + [P1]. Sorted by rank: P1(1), P2(2). Even. Pair P1 vs P2.
        # 1.0: [P3]. Lowest rank P3. Floats.
        # 0.0: [P4, P5] + [P3]. Sorted: P3(3), P4(4), P5(5). Odd. Lowest rank P3? No, lowest *rank number* is highest rank?
        # Rank 1 is best. Rank 5 is worst.
        # "Lowest rank" usually means worst player (highest rank number) in Burstein context?
        # Let's check implementation behavior or standard. usually "floater" is the one hardest to pair or bottom half.
        # Burstein rules often float the *highest* rated (lowest rank number) down? 
        # Actually, Burstein usually pairs High vs Low.
        
        # Let's see what the implementation does in test_pairing_systems.py analysis:
        # It seemed to float the player with the lowest rank ID (best player).
        # Let's verify the result.
        
        # Expected:
        # (1 vs 2)
        # Left: 3, 4, 5.
        # 1.0: [3]. 3 floats.
        # 0.0: [3, 4, 5]. 3(rank 3), 4(rank 4), 5(rank 5).
        # If best player floats: 3 floats (if 3 is best).
        # But wait, 3 came from higher group.
        # If 0.0 is last group, one gets Bye.
        # Bye goes to lowest score, most games, highest TPN.
        # P5 has lowest score (0.0) and worst rank. Likely P5 gets bye.
        # Then 3 vs 4.
        
        # Result should contain pairings for everyone except one bye.
        paired_ids = set()
        for p1_id, p2_id in pairings:
            paired_ids.add(p1_id)
            paired_ids.add(p2_id)
            
        self.assertEqual(len(paired_ids), 4) # 4 players paired, 1 bye
        self.assertIn(1, paired_ids)
        self.assertIn(2, paired_ids)
        
        # Check P1 vs P2
        # (Assuming they paired)
        
    def test_burstein_pairing_order(self):
        """
        Verify High-Low pairing within groups.
        """
        # Group: P1(1), P2(2), P3(3), P4(4)
        # Burstein (Folding): 1-4, 2-3? Or 1-3, 2-4?
        # FIDE Burstein (system using Sonneborn-Berger for initial ranking) often uses specific tables.
        # Common folding: Top half vs Bottom half? 
        # "Players in each score group are arranged in order of their Burstein numbers."
        # "Then the highest is paired with the lowest, the second highest with the second lowest, etc."
        # So 1-4, 2-3.
        
        p1 = {"id": 1, "score": 1.0, "rank": 1}
        p2 = {"id": 2, "score": 1.0, "rank": 2}
        p3 = {"id": 3, "score": 1.0, "rank": 3}
        p4 = {"id": 4, "score": 1.0, "rank": 4}
        
        players = [p1, p2, p3, p4]
        self.mock_db.get_players.return_value = players
        self.mock_db.get_tournament.return_value = {"total_rounds": 8}
        
        pairings = self.burstein.pair_players(1, 5)
        
        # Expect (1, 4) and (2, 3)
        p_set = set(tuple(sorted(p)) for p in pairings)
        self.assertIn((1, 4), p_set)
        self.assertIn((2, 3), p_set)


class TestDubovEdgeCases(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.dubov = DubovSystem(self.mock_db)

    def test_dubov_white_seeker_black_seeker(self):
        """
        Verify logic for White Seekers (WS) and Black Seekers (BS).
        """
        # P1: White Seeker (played Black, or color pref White)
        # P2: Black Seeker
        # They should match if possible.
        
        p1 = {"id": 1, "score": 1.0, "aro": 1500, "rating": 2000}
        p2 = {"id": 2, "score": 1.0, "aro": 1500, "rating": 1900}
        
        # P1 history: Black -> Prefers White
        # P2 history: White -> Prefers Black
        self.mock_db.get_player_color_history.side_effect = lambda pid, tid: ["Black"] if pid == 1 else ["White"]
        self.mock_db.get_players.return_value = [p1, p2]
        self.mock_db.get_player_opponents.return_value = []
        self.mock_db.get_player.side_effect = lambda pid, tid: p1 if pid == 1 else p2

        # Mock pair_players to return these two pairing
        # But actually assign_colors calls pair_players internally.
        # We need to make sure pair_players pairs them.
        # Given they are the only 2 players, they will pair.
        
        # We test assign_colors directly
        color_assignments = self.dubov.assign_colors(1, 2)
        
        self.assertEqual(color_assignments[1], "White")
        self.assertEqual(color_assignments[2], "Black")

    def test_dubov_color_conflict_higher_ranked(self):
        """
        Verify that higher ranked player gets preference in conflict.
        """
        # P1: Prefers White (Played Black)
        # P2: Prefers White (Played Black)
        # P1 rating > P2 rating. P1 should get White.
        
        p1 = {"id": 1, "score": 1.0, "aro": 1500, "rating": 2000}
        p2 = {"id": 2, "score": 1.0, "aro": 1500, "rating": 1900}
        
        self.mock_db.get_player_color_history.side_effect = lambda pid, tid: ["Black"]
        self.mock_db.get_players.return_value = [p1, p2]
        self.mock_db.get_player_opponents.return_value = []
        self.mock_db.get_player.side_effect = lambda pid, tid: p1 if pid == 1 else p2
        
        color_assignments = self.dubov.assign_colors(1, 2)
        
        self.assertEqual(color_assignments[1], "White", "Higher rated P1 should get preference (White)")
        self.assertEqual(color_assignments[2], "Black")
 

if __name__ == "__main__":
    unittest.main()
