"""
Pairing generation system for the Chess Pairing App.
This module implements the main pairing generation logic that integrates with all pairing systems.
"""

from typing import List, Dict, Tuple, Optional
from src.database.database import Database
from src.core.tie_break import TieBreak
from src.core.pairing.swiss_pairing import SwissPairing
from src.core.pairing.berger_table import BergerTable
from src.core.pairing.burstein_system import BursteinSystem
from src.core.pairing.dubov_system import DubovSystem
from src.core.pairing.lim_system import LimSystem
from src.core.pairing.double_swiss_system import DoubleSwissSystem
from src.core.pairing.varma_table import VarmaTable


class PairingGenerator:
    """Main pairing generation system that integrates with all pairing methods."""

    def __init__(self, db: Database):
        """Initialize the PairingGenerator with a database connection."""
        self.db = db
        self.tie_break = TieBreak(db)
        self.berger_table = BergerTable()
        self.burstein_system = BursteinSystem(db)
        self.dubov_system = DubovSystem(db)
        self.lim_system = LimSystem(db)
        self.double_swiss_system = DoubleSwissSystem(db)
        self.varma_table = VarmaTable(db)

    def generate_pairings(self, tournament_id: int, round_number: int, pairing_system: str) -> List[Dict]:
        """
        Generate pairings for a round using the appropriate pairing system.
        
        Args:
            tournament_id: ID of the tournament
            round_number: Number of the round to generate
            pairing_system: The chosen pairing system (e.g., "Swiss System", "Berger Table")
            
        Returns:
            List of pairing dictionaries containing player1_id, player2_id, and color info
        """
        # Get tournament details to check if it's a team tournament
        tournament = self._get_tournament_details(tournament_id)
        if not tournament:
            raise ValueError(f"Tournament with ID {tournament_id} not found")

        is_team_tournament = tournament["is_team_tournament"]

        # Get players for the tournament
        if is_team_tournament:
            players = self.db.get_teams(tournament_id)
            if not players:
                # Check for potential configuration mismatch
                individual_players = self.db.get_players(tournament_id)
                if individual_players:
                    raise ValueError(
                        "Tournament is configured as a Team Tournament, but no teams are registered. "
                        f"Found {len(individual_players)} individual players. "
                        "Did you mean to create an Individual Tournament?"
                    )
                else:
                    raise ValueError("No teams registered for this tournament.")
        else:
            players = self.db.get_players(tournament_id)
            if not players:
                # Check for potential configuration mismatch
                teams = self.db.get_teams(tournament_id)
                if teams:
                     raise ValueError(
                        "Tournament is configured as an Individual Tournament, but teams are registered. "
                        f"Found {len(teams)} teams. "
                        "Did you mean to create a Team Tournament?"
                    )
                else:
                    raise ValueError("No players registered for this tournament.")

        # Filter out withdrawn players
        active_players = [p for p in players if not p.get('withdrawn')]
        
        # Patch active_players (teams) with default elo if missing
        if is_team_tournament:
            for p in active_players:
                if 'elo' not in p:
                    p['elo'] = 0 # Default Elo for teams if not calculated
                if 'id' in p and 'fide_id' not in p:
                     p['fide_id'] = f"TEAM{p['id']}"
                if 'federation' not in p:
                     p['federation'] = 'UNK'

        # Update player scores before pairing
        self._update_player_scores(active_players, tournament_id, is_team_tournament)

        # Initialize pairing numbers for Berger/Varma if needed (Round 1)
        if round_number == 1 and pairing_system in ["Berger Table", "Varma Table"]:
            has_pairing_numbers = any(p.get('pairing_number') for p in active_players)
            if not has_pairing_numbers:
                if pairing_system == "Varma Table":
                    active_players = self.varma_table.assign_pairing_numbers(active_players, tournament_id)
                else:
                    # For standard Berger, seed by Elo (descending)
                    # Create a copy to sort for assignment, but we update the original objects/DB
                    sorted_players = sorted(active_players, key=lambda x: -int(x.get("elo") or 0))
                    for i, p in enumerate(sorted_players):
                        p['pairing_number'] = i + 1
                        self.db.update_player_pairing_number(p['id'], i + 1)
                    # Update active_players list to reflect sorted order (optional, but good for consistency)
                    active_players = sorted_players

        # Apply FIDE rules for pairing
        players = self._apply_fide_rules(active_players, tournament_id, round_number, pairing_system)

        # Generate pairings based on the selected system
        if pairing_system in ["Swiss System", "Dutch System"]:
            pairings = self._generate_dutch_pairings(players, tournament_id, round_number)
        elif pairing_system == "Berger Table":
            pairings = self._generate_berger_pairings(players, tournament_id, round_number)
        elif pairing_system == "Varma Table":
            pairings = self._generate_berger_pairings(players, tournament_id, round_number)
        elif pairing_system == "Burstein System":
            pairings = self._generate_burstein_pairings(players, tournament_id, round_number)
        elif pairing_system == "Dubov System":
            pairings = self._generate_dubov_pairings(players, tournament_id, round_number)
        elif pairing_system == "Lim System":
            pairings = self._generate_lim_pairings(players, tournament_id, round_number)
        elif pairing_system == "Double Swiss System":
            pairings = self._generate_double_swiss_pairings(players, tournament_id, round_number)
        else:
            # Default to Dutch pairing if system is not recognized
            pairings = self._generate_dutch_pairings(players, tournament_id, round_number)

        return pairings

    def _get_tournament_details(self, tournament_id: int) -> Optional[Dict]:
        """Get tournament details from database."""
        self.db.cursor.execute(
            "SELECT * FROM Tournaments WHERE id = ?",
            (tournament_id,)
        )
        row = self.db.cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "start_date": row[2],
                "number_of_rounds": row[3],
                "pairing_system": row[4],
                "is_team_tournament": bool(row[5])
            }
        return None

    def _apply_fide_rules(self, players: List[Dict], tournament_id: int, round_number: int, pairing_system: str = "Swiss System") -> List[Dict]:
        """
        Apply FIDE rules to the player list before pairing.
        
        FIDE rules implemented:
        1. Players are sorted by score (descending) and then by rating (descending)
           (For Berger/Varma, sorted by pairing_number)
        2. Players from the same federation should not be paired in early rounds if possible
        3. Color alternation rules
        4. No player should get the same color three times in a row
        """
        if pairing_system in ["Berger Table", "Varma Table"]:
            # For Berger systems, sort by pairing_number (ascending)
            # Use float('inf') for missing numbers to put them at the end
            players.sort(key=lambda x: (x.get("pairing_number") or float('inf'), x.get("id")))
        else:
            # Sort players by score (descending) and then by rating/elo (descending)
            # Handle cases where score or elo might be None
            players.sort(key=lambda x: (
                -int(x.get("score") or 0),
                -int(x.get("elo") or 0)
            ))

        # Add FIDE-specific attributes
        for player in players:
            player["fide_id"] = player.get("fide_id", f"FIDE{player["id"]}")
            player["federation"] = player.get("federation", "UNK")
            player["color_history"] = player.get("color_history", [])

        return players

    def _update_player_scores(self, players: List[Dict], tournament_id: int, is_team_tournament: bool = False):
        """Update scores for all players."""
        if is_team_tournament:
            # Simple score calculation for teams based on TeamResults
            # Ideally TieBreak class should handle this
            teams = self.db.get_teams(tournament_id)
            # get_teams returns score=0 by default in current impl, need to calculate it
            # Fetch all team results
            rounds = self.db.get_rounds(tournament_id)
            team_scores = {t['id']: 0.0 for t in teams}
            
            for r in rounds:
                results = self.db.get_team_results(r['id'])
                for res in results:
                    if res['is_bye']:
                        team_scores[res['team1_id']] += 1.0 # Bye is usually 1 point (or match win)
                    elif res['winner_id'] is not None:
                         if res['winner_id'] == 0:
                             team_scores[res['team1_id']] += 0.5
                             team_scores[res['team2_id']] += 0.5
                         elif res['winner_id'] == res['team1_id']:
                             team_scores[res['team1_id']] += 1.0
                         else:
                             team_scores[res['team2_id']] += 1.0
            
            for player in players:
                player['score'] = team_scores.get(player['id'], 0.0)
                
        else:
            # Calculate standings which include scores
            standings = self.tie_break.calculate_tie_breaks(tournament_id)
            score_map = {p['id']: p['score'] for p in standings}
            
            for player in players:
                player['score'] = score_map.get(player['id'], 0)

    def _generate_dutch_pairings(self, players: List[Dict], tournament_id: int, round_number: int) -> List[Dict]:
        """
        Generate FIDE-compliant Dutch system pairings.
        """
        # SwissPairing currently is tightly coupled to Player Results.
        # For Team tournaments, we might need a dedicated TeamSwissPairing or modify SwissPairing.
        # However, verifying SwissPairing content:
        # It uses db.get_player_color_history, db.get_all_tournament_results.
        # If we are in a team tournament, we need to adapt this.
        
        # Check if tournament is team-based
        tournament = self._get_tournament_details(tournament_id)
        is_team = tournament.get("is_team_tournament", False)
        
        if is_team:
            # Basic Swiss for Teams (Sort by Score, then pair neighbors)
            # This is a placeholder for full Dutch Team System
            players.sort(key=lambda x: -x.get('score', 0))
            
            pairings = []
            paired_ids = set()
            
            # Handle odd number of teams (Bye)
            bye_player_id = None
            if len(players) % 2 != 0:
                # Give bye to lowest score who hasn't had bye
                # Simplified: give to last player
                bye_player = players.pop()
                bye_player_id = bye_player['id']
            
            for i in range(0, len(players), 2):
                if i + 1 < len(players):
                    pairings.append({
                        "player1_id": players[i]['id'],
                        "player2_id": players[i+1]['id'],
                        "player1_color": None, # Colors assigned per board later
                        "player2_color": None,
                        "board_number": (i // 2) + 1
                    })
            
            if bye_player_id:
                pairings.append({
                    "player1_id": bye_player_id,
                    "player2_id": None,
                    "is_bye": True,
                    "board_number": len(pairings) + 1
                })
                
            return pairings

        swiss_pairing = SwissPairing(self.db, tournament_id, round_number, players)
        result = swiss_pairing.pair_round()
        
        if isinstance(result, tuple) and len(result) == 2:
            colored_pairings, bye_player_id = result
        else:
            colored_pairings, bye_player_id = result, None
        
        final_pairings = []
        if colored_pairings:
            for i, (p1_id, p2_id, p1_color) in enumerate(colored_pairings):
                final_pairings.append({
                    "player1_id": p1_id,
                    "player2_id": p2_id,
                    "player1_color": p1_color,
                    "player2_color": "W" if p1_color == "B" else "B",
                    "board_number": i + 1
                })
        
        if bye_player_id:
            final_pairings.append({
                "player1_id": bye_player_id,
                "player2_id": None,
                "is_bye": True,
                "board_number": len(final_pairings) + 1
            })
        
        return final_pairings

    def _allocate_dutch_colors(self, pairings: List[Tuple[int, int]], players: List[Dict], tournament_id: int, round_number: int) -> List[Dict]:
        """
        Allocate colors based on FIDE Dutch system rules from pairing_plan.md.
        """
        player_map = {p['id']: p for p in players}
        color_history = {p['id']: self.db.get_player_color_history(tournament_id, p['id']) for p in players}
        
        allocated_pairings = []

        for p1_id, p2_id in pairings:
            p1 = player_map[p1_id]
            p2 = player_map[p2_id]
            
            p1_hist = color_history.get(p1_id, [])
            p2_hist = color_history.get(p2_id, [])

            # Calculate color difference (preference)
            p1_diff = p1_hist.count('White') - p1_hist.count('Black')
            p2_diff = p2_hist.count('White') - p2_hist.count('Black')

            # Higher diff wants black, lower diff wants white
            if p1_diff > p2_diff:
                p1_color, p2_color = "Black", "White"
            elif p2_diff > p1_diff:
                p1_color, p2_color = "White", "Black"
            else:
                # Same preference, use rank (lower TPN is higher rank)
                if player_map[p1_id].get('tpn', 999) < player_map[p2_id].get('tpn', 999):
                    # p1 is higher ranked, alternate their color
                    last_color = p1_hist[-1] if p1_hist else "Black"
                    p1_color = "Black" if last_color == "White" else "White"
                    p2_color = "White" if p1_color == "Black" else "Black"
                else:
                    # p2 is higher ranked
                    last_color = p2_hist[-1] if p2_hist else "Black"
                    p2_color = "Black" if last_color == "White" else "White"
                    p1_color = "White" if p2_color == "Black" else "Black"

            allocated_pairings.append({'p1_id': p1_id, 'p2_id': p2_id, 'p1_color': p1_color, 'p2_color': p2_color})
            
        return allocated_pairings

    def _generate_berger_pairings(self, players: List[Dict], tournament_id: int, round_number: int) -> List[Dict]:
        """Generate Berger table pairings."""
        # Check if pairing numbers are used
        max_pn = 0
        use_pairing_numbers = False
        for p in players:
            if p.get("pairing_number"):
                max_pn = max(max_pn, p["pairing_number"])
                use_pairing_numbers = True
        
        if use_pairing_numbers:
            # Construct a sparse list based on pairing numbers
            # Berger table size should be at least max_pn
            # And potentially even (BergerTable handles odd by adding None, but if we have gaps, we should be careful)
            # If max_pn is 10, we need list of size 10 (indices 0..9)
            
            # Ensure size is even if we want to control the "Bye" or "Gap" explicitly?
            # Actually, just pass size max_pn. BergerTable will append None if odd.
            # But if max_pn is 10 (even), and we have 9 players (1 gap), list size is 10.
            # BergerTable uses 10.
            
            berger_player_list = [None] * max_pn
            for p in players:
                pn = p.get("pairing_number")
                if pn and 1 <= pn <= max_pn:
                    berger_player_list[pn - 1] = p["id"]
        else:
            # Standard sequential assignment
            berger_player_list = [p["id"] for p in players]

        # Use a copy since the list is modified in place
        all_rounds_pairings = self.berger_table.generate_pairings(berger_player_list.copy())

        if round_number > len(all_rounds_pairings):
            return []

        berger_pairings = all_rounds_pairings[round_number - 1]

        # Convert to our format
        pairings = []
        for i, (player1_id, player2_id) in enumerate(berger_pairings):
            pairings.append({
                "player1_id": player1_id,
                "player2_id": player2_id,
                "player1_color": "White" if i % 2 == 0 else "Black",
                "player2_color": "Black" if i % 2 == 0 else "White",
                "board_number": i + 1
            })

        # Find and add the bye player if there is one
        # Use original player IDs to find who is missing
        original_player_ids = {p["id"] for p in players}
        paired_players = {p for pair in berger_pairings for p in pair if p is not None}
        
        # Identify players who were not paired (either paired with None or not paired at all)
        bye_players = original_player_ids - paired_players
        
        if bye_players:
            # Ideally there is only one bye player per round
            # But if we have gaps, multiple people might be paired with None?
            # No, in Berger/Round Robin, everyone plays everyone.
            # In a specific round, only one person sits out (if N is odd).
            # If N is even (10), but we have a gap (PN 2 is None), then whoever plays PN 2 gets a bye.
            # That is exactly one person per round.
            
            for bye_player_id in bye_players:
                 # Need board number.
                 # Just append.
                 pairings.append({
                    "player1_id": bye_player_id,
                    "player2_id": None,
                    "player1_color": None,
                    "player2_color": None,
                    "board_number": len(pairings) + 1,
                    "is_bye": True
                })

        return pairings


    def _get_player_elo(self, player_id: int) -> int:
        """Get the Elo rating of a player."""
        self.db.cursor.execute(
            "SELECT elo FROM Players WHERE id = ?",
            (player_id,)
        )
        row = self.db.cursor.fetchone()
        return row[0] if row else 0

    def _generate_burstein_pairings(self, players: List[Dict], tournament_id: int, round_number: int) -> List[Dict]:
        """Generate Burstein system pairings."""
        # Use the existing BursteinSystem class
        burstein_pairings = self.burstein_system.pair_players(tournament_id, round_number)
        
        # Convert to our format
        pairings = []
        for i, (player1_id, player2_id) in enumerate(burstein_pairings):
            pairings.append({
                "player1_id": player1_id,
                "player2_id": player2_id,
                "player1_color": "White" if i % 2 == 0 else "Black",
                "player2_color": "Black" if i % 2 == 0 else "White",
                "board_number": i + 1
            })
        
        return pairings

    def _generate_dubov_pairings(self, players: List[Dict], tournament_id: int, round_number: int) -> List[Dict]:
        """Generate Dubov system pairings."""
        # Use the existing DubovSystem class
        dubov_pairings = self.dubov_system.pair_players(tournament_id, round_number)
        
        # Convert to our format
        pairings = []
        for i, (player1_id, player2_id) in enumerate(dubov_pairings):
            pairings.append({
                "player1_id": player1_id,
                "player2_id": player2_id,
                "player1_color": "White" if i % 2 == 0 else "Black",
                "player2_color": "Black" if i % 2 == 0 else "White",
                "board_number": i + 1
            })
        
        return pairings

    def _generate_lim_pairings(self, players: List[Dict], tournament_id: int, round_number: int) -> List[Dict]:
        """Generate Lim system pairings."""
        # Use the existing LimSystem class
        lim_pairings = self.lim_system.pair_players(tournament_id, round_number)
        
        # Convert to our format
        pairings = []
        for i, (player1_id, player2_id) in enumerate(lim_pairings):
            pairings.append({
                "player1_id": player1_id,
                "player2_id": player2_id,
                "player1_color": "White" if i % 2 == 0 else "Black",
                "player2_color": "Black" if i % 2 == 0 else "White",
                "board_number": i + 1
            })
        
        return pairings

    def _generate_double_swiss_pairings(self, players: List[Dict], tournament_id: int, round_number: int) -> List[Dict]:
        """Generate Double Swiss system pairings."""
        # Use the existing DoubleSwissSystem class
        double_swiss_pairings = self.double_swiss_system.pair_players(tournament_id, round_number)
        
        # Convert to our format
        pairings = []
        for i, (player1_id, player2_id) in enumerate(double_swiss_pairings):
            pairings.append({
                "player1_id": player1_id,
                "player2_id": player2_id,
                "player1_color": "White" if i % 2 == 0 else "Black",
                "player2_color": "Black" if i % 2 == 0 else "White",
                "board_number": i + 1
            })
        
        return pairings

    def _ensure_color_alternation(self, pairings: List[Dict], players: List[Dict], tournament_id: int, round_number: int) -> List[Dict]:
        """
        Ensure proper color alternation according to FIDE rules.
        No player should get the same color three times in a row.
        """
        # Get previous color assignments for all players
        color_history = {p['id']: self.db.get_player_color_history(tournament_id, p['id']) for p in players}
        
        for i, pairing in enumerate(pairings):
            if pairing.get("is_bye"):
                continue
                
            player1_id = pairing["player1_id"]
            player2_id = pairing["player2_id"]
            
            # Get previous colors for both players
            player1_prev_colors = color_history.get(player1_id, [])
            player2_prev_colors = color_history.get(player2_id, [])
            
            # Determine colors based on FIDE rules
            # Rule 1: Players with the same score should alternate colors
            # Rule 2: No player should get the same color three times in a row
            # Rule 3: In first round, higher rated player gets white
            
            if round_number != 1:
                # Subsequent rounds: use color history and FIDE rules
                # Check if either player has had the same color twice in a row
                player1_last_two = player1_prev_colors[-2:] if len(player1_prev_colors) >= 2 else []
                player2_last_two = player2_prev_colors[-2:] if len(player2_prev_colors) >= 2 else []
                
                # If both players have had the same color twice, alternate
                if len(player1_last_two) == 2 and player1_last_two[0] == player1_last_two[1]:
                    if len(player2_last_two) == 2 and player2_last_two[0] == player2_last_two[1]:
                        # Both players need to alternate, so assign opposite colors
                        if i % 2 == 0:
                            pairing["player1_color"] = "White"
                            pairing["player2_color"] = "Black"
                        else:
                            pairing["player1_color"] = "Black"
                            pairing["player2_color"] = "White"
                    else:
                        # Only player1 needs to alternate
                        if player1_prev_colors[-1] == "White":
                            pairing["player1_color"] = "Black"
                            pairing["player2_color"] = "White"
                        else:
                            pairing["player1_color"] = "White"
                            pairing["player2_color"] = "Black"
                elif len(player2_last_two) == 2 and player2_last_two[0] == player2_last_two[1]:
                    # Only player2 needs to alternate
                    if player2_prev_colors[-1] == "White":
                        pairing["player1_color"] = "White"
                        pairing["player2_color"] = "Black"
                    else:
                        pairing["player1_color"] = "Black"
                        pairing["player2_color"] = "White"
                else:
                    # Normal alternation based on board number
                    if i % 2 == 0:
                        pairing["player1_color"] = "White"
                        pairing["player2_color"] = "Black"
                    else:
                        pairing["player1_color"] = "Black"
                        pairing["player2_color"] = "White"
        
        return pairings

    def _avoid_same_federation_pairings(self, pairings: List[Dict], players: List[Dict]) -> List[Dict]:
        """
        Avoid pairing players from the same federation in early rounds when possible.
        This is a FIDE recommendation to promote international competition.
        """
        # Create a mapping of player IDs to federations
        player_federations = {player["id"]: player["federation"] for player in players}
        
        # Check for same-federation pairings and try to swap
        for i in range(len(pairings)):
            pairing = pairings[i]
            if pairing.get("is_bye"):
                continue
                
            player1_id = pairing["player1_id"]
            player2_id = pairing["player2_id"]
            
            if player1_id and player2_id:
                fed1 = player_federations.get(player1_id, "UNK")
                fed2 = player_federations.get(player2_id, "UNK")
                
                # If same federation, try to find a swap
                if fed1 == fed2 and fed1 != "UNK":
                    # Look for another pairing with different federations to swap with
                    for j in range(i + 1, len(pairings)):
                        other_pairing = pairings[j]
                        if other_pairing.get("is_bye"):
                            continue
                            
                        other_player1_id = other_pairing["player1_id"]
                        other_player2_id = other_pairing["player2_id"]
                        
                        if other_player1_id and other_player2_id:
                            other_fed1 = player_federations.get(other_player1_id, "UNK")
                            other_fed2 = player_federations.get(other_player2_id, "UNK")
                            
                            # If this pairing has different federations, swap one player
                            if other_fed1 != other_fed2:
                                # Swap player2_id with other_player1_id
                                pairings[i]["player2_id"] = other_player1_id
                                pairings[j]["player1_id"] = player2_id
                                break
        
        return pairings
