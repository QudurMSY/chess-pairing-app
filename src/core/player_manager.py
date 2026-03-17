
import os
import re
from typing import List, Dict, Optional, Any, Tuple
from src.database.database import Database


class PlayerManager:
    """Manages player registration and Elo management."""

    def __init__(self, db: Database):
        """Initialize the PlayerManager with a database connection."""
        self.db = db

    def add_player(self, name: str, elo: int, tournament_id: int, fide_id: str = None, federation: str = "UNK") -> int:
        """Add a player to the database."""
        return self.db.add_player(name, elo, tournament_id, fide_id, federation)

    def get_players(self, tournament_id: int) -> List[Dict]:
        """Get all players for a tournament."""
        return self.db.get_players(tournament_id)

    def withdraw_player(self, player_id: int) -> bool:
        """Mark a player as withdrawn."""
        self.db.cursor.execute(
            "UPDATE Players SET withdrawn = TRUE WHERE id = ?",
            (player_id,)
        )
        self.db.connection.commit()
        return self.db.cursor.rowcount > 0

    def update_player_elo(self, player_id: int, new_elo: int) -> bool:
        """Update a player's Elo rating."""
        self.db.cursor.execute(
            "UPDATE Players SET elo = ? WHERE id = ?",
            (new_elo, player_id)
        )
        self.db.connection.commit()
        return self.db.cursor.rowcount > 0

    def get_player_by_id(self, player_id: int) -> Optional[Dict]:
        """Get a player by their ID."""
        self.db.cursor.execute(
            "SELECT * FROM Players WHERE id = ?",
            (player_id,)
        )
        row = self.db.cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "elo": row[2],
                "tournament_id": row[3],
                "fide_id": row[4],
                "federation": row[5]
            }
        return None

    def delete_player(self, player_id: int) -> bool:
        """Delete a player from the database."""
        self.db.cursor.execute(
            "DELETE FROM Players WHERE id = ?",
            (player_id,)
        )
        self.db.connection.commit()
        return self.db.cursor.rowcount > 0

    def import_players_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Orchestrates the import process. detects file type and calls the appropriate parser.
        """
        if not os.path.exists(file_path):
            return {
                "success": False,
                "players": [],
                "errors": [f"File not found: {file_path}"],
                "count": 0
            }

        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.txt':
                players, errors = self._parse_txt_file(file_path)
            else:
                return {
                    "success": False,
                    "players": [],
                    "errors": [f"Unsupported file format: {ext}"],
                    "count": 0
                }
                
            return {
                "success": True,
                "players": players,
                "errors": errors,
                "count": len(players)
            }
            
        except Exception as e:
            return {
                "success": False,
                "players": [],
                "errors": [f"Unexpected error during import: {str(e)}"],
                "count": 0
            }

    def parse_player_line(self, line: str) -> Optional[Dict]:
        """Parses a single line of text to extract player information based on the new logic."""
        line = line.strip()
        if not line or line.startswith("#"):
            return None

        parts = line.split()
        if len(parts) < 3:  # Must have at least name, surname, and one of (elo, fide_id, federation)
            return None

        federation, fide_id, elo = None, None, None
        
        last_part = parts[-1]
        
        # Check for Federation
        if last_part.isalpha():
            federation = last_part
            parts = parts[:-1]
            if not parts: return None
            last_part = parts[-1]

        # Check for FIDE ID
        if last_part.isdigit() and 6 <= len(last_part) <= 9:
            fide_id = last_part
            parts = parts[:-1]
            if not parts: return None
            last_part = parts[-1]

        # Check for Elo
        if last_part.isdigit():
            try:
                elo = int(last_part)
                parts = parts[:-1]
            except ValueError:
                return None
        
        if len(parts) < 2:  # Must have at least a first name and a last name
            return None
        
        # The rest is name and surname
        surname = parts[-1]
        name = " ".join(parts[:-1])

        return {
            "name": f"{name} {surname}",
            "elo": elo if elo is not None else 0,
            "fide_id": fide_id,
            "federation": federation if federation is not None else "UNK"
        }

    def _parse_txt_file(self, file_path: str) -> Tuple[List[Dict], List[str]]:
        players = []
        errors = []
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                parsed_data = self.parse_player_line(line)
                if parsed_data:
                    players.append(parsed_data)
                elif line.strip() and not line.strip().startswith("#"):
                    errors.append(f"Line {i+1}: Invalid or incomplete player data.")
        return players, errors