"""
Lim system module for the Chess Pairing App.
This module implements the Lim system pairing logic according to FIDE rules.
"""

from typing import List, Dict, Tuple, Optional, Set
from src.database.database import Database
import math

class LimSystem:
    """Implements the Lim system pairing logic."""

    def __init__(self, db: Database):
        """Initialize the LimSystem with a database connection."""
        self.db = db

    def create_pairings(self, tournament_id: int, round_number: int) -> List[Tuple[int, int]]:
        """
        Creates pairings for a given round in a tournament using the Lim system.

        Args:
            tournament_id: The ID of the tournament.
            round_number: The current round number.

        Returns:
            A list of tuples, where each tuple represents a pairing (player1_id, player2_id).
        """
        players = self.db.get_players(tournament_id)
        
        bye_player_id = self.handle_bye(players)
        if bye_player_id:
            players = [p for p in players if p["id"] != bye_player_id]

        score_groups = self._group_by_score(players)
        
        median_score = (round_number - 1) / 2
        
        top_groups_scores = sorted([s for s in score_groups if s > median_score], reverse=True)
        bottom_groups_scores = sorted([s for s in score_groups if s < median_score])
        median_group_scores = [s for s in score_groups if s == median_score]
        pairing_order = top_groups_scores + bottom_groups_scores + median_group_scores

        pairings = []
        unpaired_pool = []
        pairing_history = self._get_pairing_history(tournament_id)

        for score in pairing_order:
            current_group = score_groups.get(score, [])
            current_group.extend(unpaired_pool)
            unpaired_pool = []

            current_group.sort(key=lambda p: p["tpn"], reverse=True)

            if len(current_group) % 2 != 0:
                # The lowest-rated player becomes a floater
                unpaired_pool.append(current_group.pop())

            n = len(current_group)
            s1 = current_group[:n//2]
            s2 = current_group[n//2:]

            paired_in_group = set()
            
            # Create a list of available players in s2 to pair against
            available_s2 = list(s2)

            for p1 in s1:
                for p2 in available_s2:
                    if self._are_compatible(p1["id"], p2["id"], pairing_history):
                        pairings.append((p1["id"], p2["id"]))
                        paired_in_group.add(p1["id"])
                        paired_in_group.add(p2["id"])
                        available_s2.remove(p2)
                        break
            
            for p in current_group:
                if p["id"] not in paired_in_group:
                    unpaired_pool.append(p)
        
        # Fallback for any remaining players
        if len(unpaired_pool) >= 2:
            unpaired_pool.sort(key=lambda p: p["rating"], reverse=True)
            for i in range(0, len(unpaired_pool) - 1, 2):
                p1 = unpaired_pool[i]
                p2 = unpaired_pool[i+1]
                if self._are_compatible(p1["id"], p2["id"], pairing_history):
                    pairings.append((p1["id"], p2["id"]))
                            
        return pairings

    def handle_bye(self, players: List[Dict]) -> Optional[int]:
        """
        Handles bye assignment for a round. The bye is given to the lowest-ranked 
        player in the lowest score group if there is an odd number of players.
        """
        if len(players) % 2 == 0:
            return None

        # Group by score to find the lowest score group
        score_groups = self._group_by_score(players)
        lowest_score = min(score_groups.keys())
        lowest_score_group = score_groups[lowest_score]

        # Find the lowest-ranked player in this group
        lowest_score_group.sort(key=lambda p: p["rating"])
        
        return lowest_score_group[0]["id"]


    def _group_by_score(self, players: List[Dict]) -> Dict[float, List[Dict]]:
        """Groups players by their scores."""
        score_groups = {}
        for player in players:
            score = player.get("score", 0.0)
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(player)
        return score_groups
        
    def _get_pairing_history(self, tournament_id: int) -> Dict[int, Set[int]]:
        """
        Retrieves the pairing history for a tournament.
        
        Returns:
            A dictionary where keys are player IDs and values are sets of opponent IDs.
        """
        history = {}
        rounds = self.db.get_rounds(tournament_id)
        for r in rounds:
            results = self.db.get_results(r["id"])
            for res in results:
                p1_id, p2_id = res["player1_id"], res["player2_id"]
                if p1_id not in history: history[p1_id] = set()
                if p2_id not in history: history[p2_id] = set()
                history[p1_id].add(p2_id)
                history[p2_id].add(p1_id)
        return history

    def _are_compatible(self, p1_id: int, p2_id: int, history: Dict[int, Set[int]]) -> bool:
        """
        Checks if two players have played against each other before.
        A full implementation would also check color constraints.
        """
        if p1_id in history and p2_id in history[p1_id]:
            return False
        return True
