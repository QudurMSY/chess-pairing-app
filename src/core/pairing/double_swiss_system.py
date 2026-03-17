"""
Double Swiss system module for the Chess Pairing App.
This module implements the Double Swiss system pairing logic, compliant with FIDE rules.
"""

from typing import List, Dict, Tuple, Optional
from src.database.database import Database

class DoubleSwissSystem:
    """Implements the Double Swiss system pairing logic."""

    def __init__(self, db: Database):
        """Initialize the DoubleSwissSystem with a database connection."""
        self.db = db

    def create_pairings(self, tournament_id: int, round_number: int) -> List[Tuple[int, Optional[int]]]:
        """
        Create pairings for a round using the Double Swiss system.
        This method replaces the previous pair_players, assign_colors, and handle_bye methods.
        """
        players = self.db.get_players(tournament_id)
        
        # Filter out inactive players
        players = [p for p in players if p.get('active', 1) == 1]

        # Sort players by score (descending) and then by TPN (ascending)
        players.sort(key=lambda x: (-(x.get('score') or 0), str(x.get('tpn') or "")))

        paired_players = set()
        pairings = []
        
        # Handle bye if there is an odd number of players
        bye_player_id = self._assign_bye(players, paired_players, tournament_id)
        if bye_player_id:
            paired_players.add(bye_player_id)
            pairings.append((bye_player_id, None))

        # Group players by score
        score_groups = self._group_by_score(players)

        # Main pairing loop
        for score in sorted(score_groups.keys(), reverse=True):
            score_group = [p for p in score_groups[score] if p['id'] not in paired_players]
            
            while len(score_group) > 1:
                player1 = score_group.pop(0)
                
                # Find a suitable opponent
                opponent = self._find_opponent(player1, score_group, paired_players, tournament_id)
                
                if opponent:
                    pairings.append((player1['id'], opponent['id']))
                    paired_players.add(player1['id'])
                    paired_players.add(opponent['id'])
                    score_group.remove(opponent)
                else:
                    # Handle floaters
                    floater_opponent = self._find_floater_opponent(player1, score_groups, paired_players, tournament_id)
                    if floater_opponent:
                        pairings.append((player1['id'], floater_opponent['id']))
                        paired_players.add(player1['id'])
                        paired_players.add(floater_opponent['id'])
                        # Remove floater from their original group
                        for s in score_groups:
                            score_groups[s] = [p for p in score_groups[s] if p['id'] != floater_opponent['id']]

        return pairings

    def _assign_bye(self, players: List[Dict], paired_players: set, tournament_id: int) -> Optional[int]:
        """Assigns a bye to the lowest-ranked player who has not yet received one."""
        if len(players) % 2 == 0:
            return None

        for player in reversed(players):
            if not self.db.has_player_received_bye(tournament_id, player['id']):
                return player['id']
        return None

    def _group_by_score(self, players: List[Dict]) -> Dict[float, List[Dict]]:
        """Groups players by their scores."""
        score_groups = {}
        for player in players:
            score = player.get('score', 0)
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(player)
        return score_groups

    def _find_opponent(self, player: Dict, opponents: List[Dict], paired_players: set, tournament_id: int) -> Optional[Dict]:
        """Finds a valid opponent for a player within the same score group."""
        for opponent in opponents:
            if opponent['id'] not in paired_players and not self._have_played_before(player['id'], opponent['id'], tournament_id):
                return opponent
        return None

    def _find_floater_opponent(self, player: Dict, score_groups: Dict[float, List[Dict]], paired_players: set, tournament_id: int) -> Optional[Dict]:
        """Finds a floater opponent from a lower score group."""
        current_score = player.get('score', 0)
        lower_scores = sorted([s for s in score_groups.keys() if s < current_score], reverse=True)

        for score in lower_scores:
            for opponent in score_groups[score]:
                if opponent['id'] not in paired_players and not self._have_played_before(player['id'], opponent['id'], tournament_id):
                    return opponent
        return None

    def _have_played_before(self, player1_id: int, player2_id: int, tournament_id: int) -> bool:
        """Checks if two players have played against each other before."""
        previous_opponents = self.db.get_previous_opponents(tournament_id, player1_id)
        return player2_id in previous_opponents
