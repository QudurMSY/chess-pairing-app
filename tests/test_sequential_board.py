
import unittest
from unittest.mock import MagicMock
from src.core.team_manager import TeamManager

class TestTeamManagerSequentialBoard(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.team_manager = TeamManager(self.db)

    def test_add_player_sequential_order(self):
        # Mock get_team_players to return an empty list initially
        self.team_manager.get_team_players = MagicMock(return_value=[])
        
        # Adding board 1 should succeed
        self.team_manager.add_player_to_team(1, 101, 1)
        self.db.add_team_player.assert_called_with(1, 101, 1)
        
        # Mock get_team_players to return board 1
        self.team_manager.get_team_players.return_value = [{"board_order": 1, "player_id": 101}]
        
        # Adding board 2 should succeed
        self.team_manager.add_player_to_team(1, 102, 2)
        self.db.add_team_player.assert_called_with(1, 102, 2)

    def test_add_player_out_of_order(self):
        # Mock get_team_players to return an empty list
        self.team_manager.get_team_players = MagicMock(return_value=[])
        
        # Adding board 2 before board 1 should fail
        with self.assertRaises(ValueError) as cm:
            self.team_manager.add_player_to_team(1, 102, 2)
        self.assertEqual(str(cm.exception), "Invalid board order. Next board must be 1")

    def test_add_player_duplicate_board(self):
        # Mock get_team_players to return board 1
        self.team_manager.get_team_players = MagicMock(return_value=[{"board_order": 1, "player_id": 101}])
        
        # Adding board 1 again should fail
        with self.assertRaises(ValueError) as cm:
            self.team_manager.add_player_to_team(1, 102, 1)
        self.assertEqual(str(cm.exception), "Board order 1 is already taken for team 1")

if __name__ == "__main__":
    unittest.main()
