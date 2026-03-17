"""
Round management module for the Chess Pairing App.
This module handles round creation, management, and result recording.
"""

import logging
from typing import List, Dict, Optional, Tuple
from src.database.database import Database
from src.core.pairing.pairing_generator import PairingGenerator
from src.core.tournament_manager import TournamentManager

logger = logging.getLogger(__name__)


class RoundManager:
    """Manages round creation and result recording."""

    def __init__(self, db: Database, tournament_manager: TournamentManager):
        """Initialize the RoundManager with a database connection and TournamentManager."""
        self.db = db
        self.tournament_manager = tournament_manager
        self.pairing_generator = PairingGenerator(db)

    def create_round(self, tournament_id: int, round_number: int) -> int:
        """Create a new round for a tournament."""
        return self.db.add_round(tournament_id, round_number)

    def check_previous_round_completion(self, tournament_id: int, round_number: int) -> Tuple[bool, str]:
        """Check if the previous round is complete before creating a new round."""
        try:
            # Get all rounds for the tournament
            rounds = self.get_rounds(tournament_id)
            
            # If no rounds exist, allow first round creation
            if not rounds:
                return True, "No previous rounds to check."
            
            # Get the most recent round (last round)
            previous_round = rounds[-1]
            previous_round_number = previous_round['round_number']
            
            # Only check if we're not creating the first round
            if round_number <= previous_round_number:
                return True, f"Round {round_number} is not after the last completed round."
            
            if not self.is_round_complete(previous_round['id']):
                # Get incomplete count for detailed message
                player_results = self.get_round_results(previous_round['id'])
                team_results = self.get_team_round_results(previous_round['id'])
                
                incomplete_count = 0
                if team_results:
                    incomplete_count = len([r for r in team_results if r['winner_id'] is None and not r['is_bye']])
                elif player_results:
                    incomplete_count = len([r for r in player_results if r['winner_id'] is None and not r['is_bye']])
                
                error_message = (
                    f"Cannot create round {round_number}: "
                    f"{incomplete_count} game(s) in round {previous_round_number} have no results. "
                    f"Please complete all games before creating the next round."
                )
                return False, error_message
            
            return True, f"All games in round {previous_round_number} are complete."
            
        except Exception as e:
            return False, f"Error checking round completion: {str(e)}"

    def is_round_complete(self, round_id: int) -> bool:
        """Check if all games in a round have a result."""
        player_results = self.get_round_results(round_id)
        team_results = self.get_team_round_results(round_id)
        
        if not player_results and not team_results:
            return False

        if team_results:
            for r in team_results:
                if not r['is_bye'] and r['winner_id'] is None:
                    return False
            return True
        
        if player_results:
            for r in player_results:
                if not r['is_bye'] and r['winner_id'] is None:
                    return False
            return True
            
        return True

    def create_round_with_pairings(self, tournament_id: int, round_number: int) -> int:
        """Create a new round with real pairings for a tournament."""
        # Check if previous round is complete
        is_complete, message = self.check_previous_round_completion(tournament_id, round_number)
        
        if not is_complete:
            raise ValueError(message)
        
        # Create the round first
        round_id = self.db.add_round(tournament_id, round_number)
        
        # Retrieve the pairing system for the tournament
        tournament = self.tournament_manager.get_tournament_by_id(tournament_id)
        if not tournament:
            raise ValueError(f"Tournament with ID {tournament_id} not found.")
        pairing_system = tournament["pairing_system"]
        is_team_tournament = tournament.get("is_team_tournament", False)

        # Generate pairings using the pairing generator
        pairings = self.pairing_generator.generate_pairings(tournament_id, round_number, pairing_system)
        
        # Store the pairings as results in the database
        for pairing in pairings:
            if is_team_tournament:
                if pairing.get('is_bye'):
                    self.db.add_team_result(
                        round_id,
                        pairing['player1_id'], # team1_id
                        None, # No team2
                        None, # Winner
                        is_bye=True
                    )
                    # Also create TeamMatch entry for consistency, though games won't be played
                    self._create_team_match_details(tournament_id, round_number, pairing['player1_id'], None, is_bye=True)
                else:
                    self.db.add_team_result(
                        round_id,
                        pairing['player1_id'], # team1_id
                        pairing['player2_id'], # team2_id
                        None, # Winner
                        is_bye=False
                    )
                    # Create detailed match and game records
                    self._create_team_match_details(tournament_id, round_number, pairing['player1_id'], pairing['player2_id'], is_bye=False)
            else:
                if pairing.get('is_bye'):
                    # Handle bye
                    self.db.add_result(
                        round_id,
                        pairing['player1_id'],
                        None,  # No player2 for bye
                        None, # No color for bye
                        None, # No color for bye
                        None,  # No winner for bye
                        is_bye=True
                    )
                else:
                    # Regular pairing
                    self.db.add_result(
                        round_id,
                        pairing['player1_id'],
                        pairing['player2_id'],
                        pairing['player1_color'],
                        'black' if pairing['player1_color'] == 'white' else 'white',
                        None,  # Winner will be set later
                        is_bye=False
                    )
        
        return round_id

    def _create_team_match_details(self, tournament_id: int, round_number: int, team1_id: int, team2_id: Optional[int], is_bye: bool):
        """
        Create detailed TeamMatches and TeamMatchGames records.
        """
        # Create TeamMatch record
        self.db.cursor.execute(
            "INSERT INTO TeamMatches (tournament_id, round_number, team1_id, team2_id, match_points_team1, match_points_team2, game_points_team1, game_points_team2) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (tournament_id, round_number, team1_id, team2_id, 0.0, 0.0, 0.0, 0.0)
        )
        team_match_id = self.db.cursor.lastrowid
        self.db.connection.commit()

        if is_bye or not team2_id:
            # Handle Bye: Maybe give full points? Usually handled at scoring time.
            # For now, we don't create games for a bye.
            return

        # Get boards_per_match
        self.db.cursor.execute("SELECT boards_per_match FROM Tournaments WHERE id = ?", (tournament_id,))
        row = self.db.cursor.fetchone()
        boards_per_match = row[0] if row else 4

        # Get players for both teams
        # We need to sort by board_order
        self.db.cursor.execute("SELECT player_id, board_order FROM TeamPlayers WHERE team_id = ? ORDER BY board_order ASC", (team1_id,))
        team1_players = self.db.cursor.fetchall() # List of (player_id, board_order)

        self.db.cursor.execute("SELECT player_id, board_order FROM TeamPlayers WHERE team_id = ? ORDER BY board_order ASC", (team2_id,))
        team2_players = self.db.cursor.fetchall()

        # Create games for each board
        for board_num in range(1, boards_per_match + 1):
            p1_id = next((p[0] for p in team1_players if p[1] == board_num), None)
            p2_id = next((p[0] for p in team2_players if p[1] == board_num), None)

            # Insert game
            self.db.cursor.execute(
                "INSERT INTO TeamMatchGames (team_match_id, board_number, player1_id, player2_id, result_player1, result_player2) VALUES (?, ?, ?, ?, ?, ?)",
                (team_match_id, board_num, p1_id, p2_id, None, None)
            )
        self.db.connection.commit()

    def record_result(self, round_id: int, player1_id: int, player2_id: Optional[int], player1_color: Optional[str], player2_color: Optional[str], winner_id: Optional[int], is_bye: bool) -> int:
        """Record the result of a game."""
        logger.debug(f"[RoundManager.record_result] round_id: {round_id}, player1_id: {player1_id}, player2_id: {player2_id}, winner_id: {winner_id}, is_bye: {is_bye}")
        return self.db.add_result(round_id, player1_id, player2_id, player1_color, player2_color, winner_id, is_bye)

    def record_team_result(self, round_id: int, team1_id: int, team2_id: int,
                           winner_id: Optional[int], is_bye: bool) -> int:
        """Record the result of a team game."""
        return self.db.add_team_result(round_id, team1_id, team2_id, winner_id, is_bye)

    def get_round_results(self, round_id: int) -> List[Dict]:
        """Get all results for a round."""
        return self.db.get_results(round_id)

    def get_rounds(self, tournament_id: int) -> List[Dict]:
        """Get all rounds for a tournament."""
        return self.db.get_rounds(tournament_id)

    def get_team_round_results(self, round_id: int) -> List[Dict]:
        """Get all team results for a round."""
        return self.db.get_team_results(round_id)

    def update_result(self, result_id: int, winner_id: Optional[int]) -> bool:
        """Update the result of a game."""
        logger.debug(f"[RoundManager.update_result] result_id: {result_id}, winner_id: {winner_id}")
        return self.db.update_result(result_id, winner_id)

    def update_team_result(self, result_id: int, winner_id: Optional[int]) -> bool:
        """Update the result of a team game."""
        self.db.cursor.execute(
            "UPDATE TeamResults SET winner_id = ? WHERE id = ?",
            (winner_id, result_id)
        )
        self.db.connection.commit()
        return self.db.cursor.rowcount > 0

    def delete_result(self, result_id: int) -> bool:
        """Delete a result from the database."""
        self.db.cursor.execute(
            "DELETE FROM Results WHERE id = ?",
            (result_id,)
        )
        self.db.connection.commit()
        return self.db.cursor.rowcount > 0

    def delete_team_result(self, result_id: int) -> bool:
        """Delete a team result from the database."""
        self.db.cursor.execute(
            "DELETE FROM TeamResults WHERE id = ?",
            (result_id,)
        )
        self.db.connection.commit()
        return self.db.cursor.rowcount > 0

    def update_team_game_result(self, match_id: int, board_number: int, result_code: str) -> bool:
        """
        Update the result of a specific board in a team match and recalculate match scores.
        
        Args:
            match_id: ID of the TeamMatch (not TeamResult)
            board_number: Board number (1-based)
            result_code: '1-0', '0-1', '1/2-1/2', '0.5-0.5', or None
        """
        # 1. Parse result
        p1_score = None
        p2_score = None
        if result_code == '1-0':
            p1_score = 1.0
            p2_score = 0.0
        elif result_code == '0-1':
            p1_score = 0.0
            p2_score = 1.0
        elif result_code in ['1/2-1/2', '0.5-0.5']:
            p1_score = 0.5
            p2_score = 0.5
        
        # 2. Update TeamMatchGames
        self.db.cursor.execute(
            "UPDATE TeamMatchGames SET result_player1 = ?, result_player2 = ? WHERE team_match_id = ? AND board_number = ?",
            (p1_score, p2_score, match_id, board_number)
        )
        self.db.connection.commit()
        
        # 3. Recalculate Team Match Score
        self._recalculate_team_match_score(match_id)
        
        return True

    def update_team_match_results_batch(self, match_id: int, board_results: List[Tuple[int, Optional[float], Optional[float]]]):
        """
        Update multiple board results for a team match and recalculate score once.
        
        Args:
            match_id: ID of the TeamMatch
            board_results: List of (board_number, p1_score, p2_score)
        """
        for board_num, p1_score, p2_score in board_results:
             self.db.cursor.execute(
                "UPDATE TeamMatchGames SET result_player1 = ?, result_player2 = ? WHERE team_match_id = ? AND board_number = ?",
                (p1_score, p2_score, match_id, board_num)
            )
        self.db.connection.commit()
        
        self._recalculate_team_match_score(match_id)

    def _recalculate_team_match_score(self, match_id: int):
        """Recalculate the total score for a team match based on individual games."""
        self.db.cursor.execute(
            "SELECT result_player1, result_player2 FROM TeamMatchGames WHERE team_match_id = ?",
            (match_id,)
        )
        games = self.db.cursor.fetchall()
        
        game_points_t1 = 0.0
        game_points_t2 = 0.0
        completed_games = 0
        total_games = len(games)
        
        for g in games:
            if g[0] is not None:
                game_points_t1 += g[0]
                game_points_t2 += g[1]
                completed_games += 1
                
        # Update TeamMatches
        # For now, match points are usually 2 for win, 1 for draw, 0 for loss, or just sum of game points?
        # FIDE usually uses match points (2, 1, 0) based on game points comparison.
        
        match_points_t1 = 0.0
        match_points_t2 = 0.0
        
        if completed_games > 0: # Only assign match points if at least one game (or maybe all?) is done. 
            # Usually match result is decided when > 50% points or all games done. 
            # Let's just calculate based on current standing.
            if game_points_t1 > game_points_t2:
                match_points_t1 = 2.0
                match_points_t2 = 0.0
            elif game_points_t2 > game_points_t1:
                match_points_t1 = 0.0
                match_points_t2 = 2.0
            elif game_points_t1 == game_points_t2 and completed_games == total_games: 
                # Draw only final if all games done? Or if mathematically impossible to win?
                # For simplicity, if scores equal, it's a draw so far.
                match_points_t1 = 1.0
                match_points_t2 = 1.0
            # If unfinished, we might leave match points as 0 or calculate provisionally?
            # Standard: Update continuously.
        
        self.db.cursor.execute(
            "UPDATE TeamMatches SET game_points_team1 = ?, game_points_team2 = ?, match_points_team1 = ?, match_points_team2 = ? WHERE id = ?",
            (game_points_t1, game_points_t2, match_points_t1, match_points_t2, match_id)
        )
        self.db.connection.commit()
        
        # 4. Sync with TeamResults (for UI compatibility)
        # We need to find the corresponding TeamResult.
        # TeamMatch has tournament_id, round_number, team1_id.
        self.db.cursor.execute("SELECT tournament_id, round_number, team1_id, team2_id FROM TeamMatches WHERE id = ?", (match_id,))
        match_info = self.db.cursor.fetchone()
        
        if match_info:
            t_id, r_num, team1_id, team2_id = match_info
            
            # Find round_id
            self.db.cursor.execute("SELECT id FROM Rounds WHERE tournament_id = ? AND round_number = ?", (t_id, r_num))
            round_row = self.db.cursor.fetchone()
            if round_row:
                round_id = round_row[0]
                
                # Determine winner for TeamResult
                winner_id = None
                if match_points_t1 > match_points_t2:
                    winner_id = team1_id
                elif match_points_t2 > match_points_t1:
                    winner_id = team2_id
                elif match_points_t1 == match_points_t2 and completed_games == total_games:
                    winner_id = 0 # Draw
                
                # Update TeamResults
                self.db.cursor.execute(
                    "UPDATE TeamResults SET winner_id = ? WHERE round_id = ? AND team1_id = ? AND team2_id = ?",
                    (winner_id, round_id, team1_id, team2_id)
                )
                self.db.connection.commit()
