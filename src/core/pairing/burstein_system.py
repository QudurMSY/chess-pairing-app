
from typing import List, Dict, Tuple

from src.core.pairing.swiss_pairing import SwissPairing
from src.core.tie_break import TieBreak
from src.database.database import Database


class BursteinSystem:
    """Implements the Burstein system pairing logic."""

    def __init__(self, db: Database):
        """Initialize the BursteinSystem with a database connection."""
        self.db = db
        self.tie_break = TieBreak(db)

    def pair_players(self, tournament_id: int, round_number: int) -> List[Tuple[int, int]]:
        """Pair players for a round using the Burstein system."""
        tournament = self.db.get_tournament(tournament_id)
        players = self.db.get_players(tournament_id)
        total_rounds = tournament["total_rounds"]
        seeding_rounds = min(4, total_rounds // 2)

        if round_number <= seeding_rounds:
            dutch_system = SwissPairing(self.db, tournament_id, round_number, players)
            pairings, _ = dutch_system.pair_round()
            return [(p1, p2) for p1, p2, color in pairings]

        players_by_score = self._group_by_score(players)

        pairings = []
        floater = None
        sorted_score_groups = sorted(players_by_score.keys(), reverse=True)

        for score in sorted_score_groups:
            score_group = players_by_score[score]
            if floater:
                score_group.append(floater)
                floater = None

            if len(score_group) % 2 != 0:
                # For simplicity, float down the player with the lowest index.
                # A more robust implementation would consider more tie-break rules.
                score_group.sort(key=lambda p: p["rank"])
                floater = score_group.pop(0)

            pairings.extend(self._pair_score_group(score_group))

        return pairings

    def _pair_score_group(self, score_group: List[Dict]) -> List[Tuple[int, int]]:
        if not score_group:
            return []

        # Sort by rank
        score_group.sort(key=lambda p: p["rank"])

        # Folding pairing
        pairings = []
        mid = len(score_group) // 2
        top_half = score_group[:mid]
        bottom_half = score_group[mid:]
        bottom_half.reverse()

        for i in range(mid):
            pairings.append((top_half[i]["id"], bottom_half[i]["id"]))

        return pairings

    def _calculate_index(self, p1: Dict, p2: Dict, round_number: int) -> int:
        """Calculates the Burstein index 'I'."""
        return p1["rank"] + p2["rank"] - round_number

    def _group_by_score(self, players: List[Dict]) -> Dict[float, List[Dict]]:
        groups = {}
        for player in players:
            score = player.get("score", 0.0)
            if score not in groups:
                groups[score] = []
            groups[score].append(player)
        return groups

    def assign_colors(self, tournament_id: int, round_number: int) -> Dict[int, str]:
        """Assign colors to players for a round based on the Burstein system."""
        pairings = self.pair_players(tournament_id, round_number)
        players = self.db.get_players(tournament_id)
        player_map = {p["id"]: p for p in players}
        color_assignments = {}

        for p1_id, p2_id in pairings:
            p1 = player_map[p1_id]
            p2 = player_map[p2_id]

            index = self._calculate_index(p1, p2, round_number)

            if index % 2 == 0:  # Even index
                # Higher ranked player gets White
                if p1["rank"] < p2["rank"]:
                    color_assignments[p1_id] = "White"
                    color_assignments[p2_id] = "Black"
                else:
                    color_assignments[p1_id] = "Black"
                    color_assignments[p2_id] = "White"
            else:  # Odd index
                # Lower ranked player gets White
                if p1["rank"] < p2["rank"]:
                    color_assignments[p1_id] = "Black"
                    color_assignments[p2_id] = "White"
                else:
                    color_assignments[p1_id] = "White"
                    color_assignments[p2_id] = "Black"

        return color_assignments

    def handle_bye(self, tournament_id: int, round_number: int) -> int:
        """Handle bye assignment for a round."""
        players = self.db.get_players(tournament_id)
        if len(players) % 2 == 0:
            return None

        # According to rules, the bye is given to the player who leaves a legal pairing
        # and has the lowest score, most games played, and largest TPN.
        # This is a simplified version.
        players.sort(key=lambda p: (p.get("score", 0), -len(self.db.get_results_for_player(p["id"])), -(p.get("tpn") or 0)))
        return players[0]["id"]
