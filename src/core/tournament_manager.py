"""
Tournament management module for the Chess Pairing App.
This module handles tournament creation, management, and related operations.
"""

from typing import List, Dict, Optional
from src.database.database import Database


class TournamentManager:
    """Manages tournament creation and management."""

    def __init__(self, db: Database):
        """Initialize the TournamentManager with a database connection."""
        self.db = db

    def create_tournament(self, name: str, start_date: str, number_of_rounds: int, 
                         pairing_system: str, is_team_tournament: bool, boards_per_match: int = 4) -> int:
        """Create a new tournament."""
        return self.db.add_tournament(name, start_date, number_of_rounds, 
                                     pairing_system, is_team_tournament, boards_per_match)

    def get_tournaments(self) -> List[Dict]:
        """Get all tournaments."""
        return self.db.get_tournaments()

    def get_tournament_by_id(self, tournament_id: int) -> Optional[Dict]:
        """Get a tournament by its ID."""
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

    def update_tournament(self, tournament_id: int, name: str, start_date: str, 
                         number_of_rounds: int, pairing_system: str, 
                         is_team_tournament: bool) -> bool:
        """Update a tournament's details."""
        self.db.cursor.execute(
            """
            UPDATE Tournaments 
            SET name = ?, start_date = ?, number_of_rounds = ?, 
                pairing_system = ?, is_team_tournament = ?
            WHERE id = ?
            """,
            (name, start_date, number_of_rounds, pairing_system, 
             is_team_tournament, tournament_id)
        )
        self.db.connection.commit()
        return self.db.cursor.rowcount > 0

    def delete_tournament(self, tournament_id: int) -> bool:
        """Delete a tournament from the database."""
        self.db.cursor.execute(
            "DELETE FROM Tournaments WHERE id = ?",
            (tournament_id,)
        )
        self.db.connection.commit()
        return self.db.cursor.rowcount > 0