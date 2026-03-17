"""
Berger table module for the Chess Pairing App.
This module implements the Berger table for round-robin tournaments.
"""

from typing import List, Tuple


class BergerTable:
    """Implements the Berger table for round-robin tournaments."""

    def generate_pairings(self, players: List[int]) -> List[List[Tuple[int, int]]]:
        """
        Generate pairings for a round-robin tournament using the Berger table algorithm.
        Handles both even and odd numbers of players.
        """
        num_players = len(players)
        if num_players % 2 != 0:
            players.append(None)  # Add a bye
            num_players += 1

        rounds = []
        for r in range(num_players - 1):
            round_pairings = []
            # Player n (last player) is fixed and plays against a rotating opponent
            p1 = players[r]
            p2 = players[num_players - 1]
            if p1 is not None and p2 is not None:
                round_pairings.append((p1, p2))

            # Pair the remaining players
            for i in range(1, num_players // 2):
                p1_idx = (r + i) % (num_players - 1)
                p2_idx = (r - i + num_players - 1) % (num_players - 1)

                p1 = players[p1_idx]
                p2 = players[p2_idx]
                if p1 is not None and p2 is not None:
                    round_pairings.append((p1, p2))
            rounds.append(round_pairings)

            # Rotate players for the next round, keeping the last player fixed
            players.insert(1, players.pop(-2))

        return rounds
