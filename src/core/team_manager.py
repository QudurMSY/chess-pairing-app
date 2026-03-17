"""
Team management module for the Chess Pairing App.
This module handles team registration, management, and related operations.
"""

from typing import List, Dict, Optional
from src.database.database import Database


class TeamManager:
    """Manages team registration and management."""

    def __init__(self, db: Database):
        """Initialize the TeamManager with a database connection."""
        self.db = db

    def add_team(self, name: str, tournament_id: int) -> int:
        """Add a team to the database."""
        return self.db.add_team(name, tournament_id)

    def calculate_team_average_rating(self, team_id: int, boards_per_match: int) -> Optional[int]:
        """Calculate and update the average rating of a team based on top N players."""
        players = self.get_team_players(team_id)
        if not players:
            return None
            
        # Get full player details to access Elo
        player_details = []
        for p in players:
            self.db.cursor.execute("SELECT elo FROM Players WHERE id = ?", (p['player_id'],))
            row = self.db.cursor.fetchone()
            if row and row[0] is not None:
                player_details.append(row[0])
                
        if not player_details:
            return 0
            
        # Sort by elo descending and take top N
        player_details.sort(reverse=True)
        top_players = player_details[:boards_per_match]
        
        avg_rating = sum(top_players) // len(top_players)
        
        # Update team in DB
        self.db.cursor.execute(
            "UPDATE Teams SET average_rating = ? WHERE id = ?",
            (avg_rating, team_id)
        )
        self.db.connection.commit()
        return avg_rating

    def add_player_to_team(self, team_id: int, player_id: int, board_order: Optional[int] = None) -> int:
        """Add a player to a team."""
        existing_players = self.get_team_players(team_id)
        existing_boards = [p["board_order"] for p in existing_players]
        max_board = max(existing_boards) if existing_boards else 0

        if board_order is None:
            board_order = max_board + 1
        else:
            if board_order in existing_boards:
                raise ValueError(f"Board order {board_order} is already taken for team {team_id}")
            if board_order != max_board + 1:
                raise ValueError(f"Invalid board order. Next board must be {max_board + 1}")

        return self.db.add_team_player(team_id, player_id, board_order)

    def reorder_team_players(self, team_id: int):
        """Automatically sort team players by Elo and assign board order."""
        players = self.get_team_players(team_id)
        
        player_elos = []
        for p in players:
            self.db.cursor.execute("SELECT elo FROM Players WHERE id = ?", (p['player_id'],))
            row = self.db.cursor.fetchone()
            elo = row[0] if row and row[0] is not None else 0
            player_elos.append((p['player_id'], elo, p['id']))
            
        # Sort by Elo descending
        player_elos.sort(key=lambda x: x[1], reverse=True)
        
        # Update board order
        for i, (p_id, elo, tp_id) in enumerate(player_elos):
            board_order = i + 1
            self.db.cursor.execute(
                "UPDATE TeamPlayers SET board_order = ? WHERE id = ?",
                (board_order, tp_id)
            )
        self.db.connection.commit()

    def get_teams(self, tournament_id: int) -> List[Dict]:
        """Get all teams for a tournament."""
        return self.db.get_teams(tournament_id)

    def get_team_players(self, team_id: int) -> List[Dict]:
        """Get all players for a team."""
        return self.db.get_team_players(team_id)

    def get_team_by_id(self, team_id: int) -> Optional[Dict]:
        """Get a team by its ID."""
        self.db.cursor.execute(
            "SELECT * FROM Teams WHERE id = ?",
            (team_id,)
        )
        row = self.db.cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "tournament_id": row[2]
        }

    def update_team(self, team_id: int, name: str) -> bool:
        """Update a team's details."""
        self.db.cursor.execute(
            "UPDATE Teams SET name = ? WHERE id = ?",
            (name, team_id)
        )
        self.db.connection.commit()
        return self.db.cursor.rowcount > 0

    def delete_team(self, team_id: int) -> bool:
        """Delete a team from the database."""
        self.db.cursor.execute(
            "DELETE FROM Teams WHERE id = ?",
            (team_id,)
        )
        self.db.connection.commit()
        return self.db.cursor.rowcount > 0