"""
Dubov system module for the Chess Pairing App.
This module implements the Dubov system pairing logic, compliant with FIDE rules.
"""

from typing import List, Dict, Tuple
from src.database.database import Database
from collections import defaultdict

class DubovSystem:
    """Implements the Dubov system pairing logic."""

    def __init__(self, db: Database):
        """Initialize the DubovSystem with a database connection."""
        self.db = db

    def _calculate_aro(self, player_id: int, tournament_id: int, round_number: int) -> float:
        """Calculate the Average Rating of Opponents (ARO) for a player."""
        opponents = self.db.get_player_opponents(player_id, tournament_id, round_number)
        if not opponents:
            return 0.0
        
        total_rating = sum(opponent['rating'] for opponent in opponents if opponent['rating'] is not None)
        return total_rating / len(opponents) if opponents else 0.0

    def pair_players(self, tournament_id: int, round_number: int) -> List[Tuple[int, int]]:
        """Pair players for a round using the Dubov system."""
        players = self.db.get_players(tournament_id)
        
        for player in players:
            player['aro'] = self._calculate_aro(player['id'], tournament_id, round_number)

        # Group players by score
        score_groups = defaultdict(list)
        for player in players:
            score = player.get('score', 0) or 0
            score_groups[score].append(player)

        # Sort score groups by score (ascending) to handle upfloaters correctly
        sorted_scores = sorted(score_groups.keys())

        pairings = []
        unpaired_players = []

        for score in sorted_scores:
            group = score_groups[score]
            
            # Add any upfloaters from the previous (lower score) group
            group.extend(unpaired_players)
            unpaired_players = []

            # Sort players within the scoregroup by ARO (ascending)
            group.sort(key=lambda p: p['aro'])
            
            # Handle odd number of players by creating an upfloater
            if len(group) % 2 != 0:
                # The player with the lowest ARO becomes an upfloater to the next higher score group.
                # Since we are iterating upwards, we pass the unpaired player to the next iteration.
                unpaired_players.append(group.pop(0)) # Lowest ARO player floats up.

            # Pair low-ARO players with high-rated players.
            # To do this, we sort the first half by ARO and the second half by rating descending.
            if len(group) > 1:
                group.sort(key=lambda p: p['aro'])
                low_aro_half = group[:len(group) // 2]
                high_aro_half = group[len(group) // 2:]

                # To pair low ARO with high rating, we sort the high_aro_half by rating descending
                high_aro_half.sort(key=lambda p: p.get('rating', 0), reverse=True)

                for player1, player2 in zip(low_aro_half, high_aro_half):
                    pairings.append((player1['id'], player2['id']))

        # If there's an unpaired player at the end (from the lowest score group), they get a bye.
        if unpaired_players:
            # In a real scenario, we would call a handle_bye function.
            # For now, we'll just note that they are unpaired.
            # The handle_bye logic should be separate.
            pass

        return pairings

    def assign_colors(self, tournament_id: int, round_number: int) -> Dict[int, str]:
        """Assign colors to players for a round based on FIDE rules."""
        pairings = self.pair_players(tournament_id, round_number)
        color_assignments = {}

        for p1_id, p2_id in pairings:
            player1 = self.db.get_player(p1_id, tournament_id)
            player2 = self.db.get_player(p2_id, tournament_id)

            if not player1 or not player2:
                continue

            # 1. Get color history
            p1_history = self.db.get_player_color_history(p1_id, tournament_id)
            p2_history = self.db.get_player_color_history(p2_id, tournament_id)

            # 2. Determine color preference
            p1_preference = self._get_color_preference(p1_history)
            p2_preference = self._get_color_preference(p2_history)

            # 3. Assign colors
            p1_color, p2_color = self._determine_colors(
                player1, player2, p1_preference, p2_preference
            )

            color_assignments[p1_id] = p1_color
            color_assignments[p2_id] = p2_color

        return color_assignments

    def _get_color_preference(self, color_history: List[str]) -> str:
        """
        Determines a player's color preference.
        A strong preference is given to avoid a third consecutive color.
        A normal preference is to balance the colors.
        """
        if len(color_history) >= 2 and color_history[-1] == color_history[-2]:
            return "White" if color_history[-1] == "Black" else "Black"  # Strong preference

        w_count = color_history.count("White")
        b_count = color_history.count("Black")

        if w_count > b_count:
            return "Black"
        if b_count > w_count:
            return "White"
        
        return "None" # No preference

    def _determine_colors(self, player1: Dict, player2: Dict, p1_pref: str, p2_pref: str) -> Tuple[str, str]:
        """Determines the color assignment for a pair of players."""
        higher_ranked = player1 if (player1.get('rating', 0) or 0) >= (player2.get('rating', 0) or 0) else player2

        # Case 1: Preferences are compatible
        if p1_pref == "White" and p2_pref == "Black":
            return "White", "Black"
        if p1_pref == "Black" and p2_pref == "White":
            return "Black", "White"

        # Case 2: One player has a preference
        if p1_pref != "None" and p2_pref == "None":
            return p1_pref, "Black" if p1_pref == "White" else "White"
        if p2_pref != "None" and p1_pref == "None":
            return "Black" if p2_pref == "White" else "White", p2_pref

        # Case 3: Preferences conflict or no preferences
        # Higher ranked player gets their preference if they have one, otherwise white.
        if higher_ranked['id'] == player1['id']:
            color_for_p1 = p1_pref if p1_pref != "None" else "White"
            color_for_p2 = "Black" if color_for_p1 == "White" else "White"
            return color_for_p1, color_for_p2
        else: # player2 is higher_ranked
            color_for_p2 = p2_pref if p2_pref != "None" else "White"
            color_for_p1 = "Black" if color_for_p2 == "White" else "White"
            return color_for_p1, color_for_p2

    def handle_bye(self, tournament_id: int, round_number: int) -> int:
        """Handle bye assignment for a round."""
        players = self.db.get_players(tournament_id)
        
        if len(players) % 2 != 0:
            # Find a player who hasn't had a bye yet, starting from the lowest score group
            # and lowest rating.
            players_by_score = sorted(players, key=lambda p: (p.get('score', 0) or 0, p.get('rating', 0) or 0))
            for player in players_by_score:
                if not self.db.has_player_received_bye(player['id'], tournament_id):
                    return player['id']
            # If all have had a bye, give it to the lowest player again
            return players_by_score[0]['id'] if players_by_score else None
        
        return None
