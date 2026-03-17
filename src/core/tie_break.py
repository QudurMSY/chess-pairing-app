"""
Tie-break systems module for the Chess Pairing App.
This module implements various tie-break systems.
"""

from typing import List, Dict
from src.database.database import Database


class TieBreak:
    """Implements various tie-break systems."""

    def __init__(self, db: Database):
        """Initialize the TieBreak with a database connection."""
        self.db = db

    def buchholz(self, tournament_id: int, player_id: int) -> float:
        """Calculate the Buchholz score for a player."""
        # Get all results for the tournament
        rounds = self.db.get_rounds(tournament_id)
        
        # Calculate the sum of opponents' scores
        total = 0.0
        for round in rounds:
            results = self.db.get_results(round['id'])
            for result in results:
                if result['player1_id'] == player_id:
                    opponent_id = result['player2_id']
                elif result['player2_id'] == player_id:
                    opponent_id = result['player1_id']
                else:
                    continue
                
                # Get the opponent's score
                if opponent_id is not None:
                    opponent_score = self._get_player_score(tournament_id, opponent_id)
                    total += opponent_score
        
        return total

    def sonneborn_berger(self, tournament_id: int, player_id: int) -> float:
        """Calculate the Sonneborn-Berger score for a player."""
        # Get all results for the tournament
        rounds = self.db.get_rounds(tournament_id)
        
        # Calculate the sum of the product of results and opponents' scores
        total = 0.0
        for round in rounds:
            results = self.db.get_results(round['id'])
            for result in results:
                # Safely cast winner_id to int
                winner_id = result['winner_id']
                if winner_id is not None:
                    try:
                        winner_id = int(winner_id)
                    except (ValueError, TypeError):
                        pass

                if result['player1_id'] == player_id:
                    opponent_id = result['player2_id']
                    if winner_id == player_id:
                        result_score = 1.0
                    elif winner_id == 0:
                        result_score = 0.5
                    else:
                        result_score = 0.0
                elif result['player2_id'] == player_id:
                    opponent_id = result['player1_id']
                    if winner_id == player_id:
                        result_score = 1.0
                    elif winner_id == 0:
                        result_score = 0.5
                    else:
                        result_score = 0.0
                else:
                    continue
                
                # Get the opponent's score
                if opponent_id is not None:
                    opponent_score = self._get_player_score(tournament_id, opponent_id)
                    total += result_score * opponent_score
        
        return total

    def direct_encounter(self, tournament_id: int, player1_id: int, player2_id: int) -> float:
        """Calculate the direct encounter score between two players."""
        # Get all results for the tournament
        rounds = self.db.get_rounds(tournament_id)
        
        # Find the result of the direct encounter
        for round in rounds:
            results = self.db.get_results(round['id'])
            for result in results:
                if (result['player1_id'] == player1_id and result['player2_id'] == player2_id) or \
                   (result['player1_id'] == player2_id and result['player2_id'] == player1_id):
                    # Safely cast winner_id to int
                    winner_id = result['winner_id']
                    if winner_id is not None:
                        try:
                            winner_id = int(winner_id)
                        except (ValueError, TypeError):
                            pass

                    if winner_id == player1_id:
                        return 1.0
                    elif winner_id == player2_id:
                        return 0.0
                    else:
                        return 0.5
        
        return 0.0

    def calculate_performance_rating(self, tournament_id: int, player_id: int, elo_cache: Dict[int, int] = None) -> float:
        """
        Calculate the performance rating for a player.
        Performance Rating = Ra + dp
        Ra = Average Rating of Opponents
        dp = Rating difference based on percentage score (p)
        """
        # Get all results for the tournament
        rounds = self.db.get_rounds(tournament_id)
        
        opponents_ratings = []
        score = 0.0
        games_with_opponents = 0
        total_games = 0

        for round_data in rounds:
            results = self.db.get_results(round_data['id'])
            for result in results:
                if not (result.get('player1_id') == player_id or result.get('player2_id') == player_id):
                    continue

                total_games += 1
                winner_id = result.get('winner_id')
                if winner_id is not None:
                    try:
                        winner_id = int(winner_id)
                    except (ValueError, TypeError):
                        pass

                if result.get('is_bye'):
                    score += 1.0
                    continue

                opponent_id = None
                if result['player1_id'] == player_id:
                    opponent_id = result['player2_id']
                    if winner_id == player_id:
                        score += 1.0
                    elif winner_id == 0:
                        score += 0.5
                elif result['player2_id'] == player_id:
                    opponent_id = result['player1_id']
                    if winner_id == player_id:
                        score += 1.0
                    elif winner_id == 0:
                        score += 0.5

                if opponent_id:
                    games_with_opponents += 1
                    if elo_cache and opponent_id in elo_cache:
                        elo = elo_cache[opponent_id]
                    else:
                        elo = self._get_player_elo(opponent_id)
                    
                    if elo is None or elo == 0:
                        elo = 1000
                    opponents_ratings.append(elo)

        if not opponents_ratings:
            return 0.0

        ra = sum(opponents_ratings) / games_with_opponents
        
        if total_games == 0:
            return 0.0

        p = score / total_games
        
        dp_table = {
            1.0: 800, 0.9: 366, 0.8: 240, 0.7: 149, 0.6: 72, 0.5: 0,
            0.4: -72, 0.3: -149, 0.2: -240, 0.1: -366, 0.0: -800
        }
        
        closest_p = min(dp_table.keys(), key=lambda k: abs(k - p))
        dp = dp_table[closest_p]
        
        return ra + dp

    def _get_player_elo(self, player_id: int) -> int:
        """Get a player's Elo from the database."""
        self.db.cursor.execute("SELECT elo FROM Players WHERE id = ?", (player_id,))
        result = self.db.cursor.fetchone()
        if result:
            return result[0]
        return 0

    def _get_player_score(self, tournament_id: int, player_id: int) -> float:
        """Get the score of a player in a tournament."""
        # Get all results for the tournament
        rounds = self.db.get_rounds(tournament_id)
        
        # Calculate the player's score
        score = 0.0
        for round in rounds:
            results = self.db.get_results(round['id'])
            for result in results:
                if result['player1_id'] == player_id or result['player2_id'] == player_id:
                    # Safely cast winner_id to int
                    winner_id = result['winner_id']
                    if winner_id is not None:
                        try:
                            winner_id = int(winner_id)
                        except (ValueError, TypeError):
                            pass

                    if winner_id == player_id:
                        score += 1.0
                    elif winner_id == 0:  # Draw
                        score += 0.5
                    elif result.get('is_bye') and (result.get('player1_id') == player_id or result.get('player2_id') == player_id):
                        # A bye always gives 1 point
                        score += 1.0
        
        return score

    def calculate_tie_breaks(self, tournament_id: int) -> List[Dict]:
        """
        Calculate scores and tie-breaks for all players in a tournament.
        Returns a list of dictionaries sorted by score (desc), then Buchholz (desc).
        """
        players = self.db.get_players(tournament_id)
        standings = []
        
        # Create Elo cache to avoid repeated DB calls
        elo_cache = {p['id']: p['elo'] for p in players}

        for player in players:
            player_id = player['id']
            score = self._get_player_score(tournament_id, player_id)
            buchholz_score = self.buchholz(tournament_id, player_id)
            sb_score = self.sonneborn_berger(tournament_id, player_id)
            
            # Calculate performance rating
            performance = self.calculate_performance_rating(tournament_id, player_id, elo_cache)

            standings.append({
                "id": player_id,
                "name": player['name'],
                "elo": player['elo'],
                "score": score,
                "buchholz": buchholz_score,
                "sonneborn_berger": sb_score,
                "performance": performance
            })

        # Sort by Score (desc), then Buchholz (desc), then Sonneborn-Berger (desc)
        standings.sort(key=lambda x: (x['score'], x['buchholz'], x['sonneborn_berger']), reverse=True)
        
        return standings