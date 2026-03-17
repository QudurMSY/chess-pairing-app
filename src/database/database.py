"""
Database module for the Chess Pairing App.
This module handles all database operations using SQLite.
"""

import sqlite3
from typing import List, Dict, Optional, Tuple


class Database:
    """Database class to manage all database operations."""

    def __init__(self, db_path: str = "chess_pairing.db"):
        """Initialize the database connection."""
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self._create_tables()
        self._migrate_schema()

    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        # Players table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                elo INTEGER,
                tournament_id INTEGER,
                fide_id TEXT,
                federation TEXT DEFAULT 'UNK',
                withdrawn BOOLEAN DEFAULT FALSE,
                pairing_number INTEGER,
                FOREIGN KEY (tournament_id) REFERENCES Tournaments(id)
            )
        """)

        # Teams table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                tournament_id INTEGER,
                seed_ranking INTEGER,
                average_rating INTEGER,
                FOREIGN KEY (tournament_id) REFERENCES Tournaments(id)
            )
        """)

        # TeamPlayers table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS TeamPlayers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER,
                player_id INTEGER,
                board_order INTEGER,
                FOREIGN KEY (team_id) REFERENCES Teams(id),
                FOREIGN KEY (player_id) REFERENCES Players(id)
            )
        """)

        # TeamMatches table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS TeamMatches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER,
                round_number INTEGER,
                team1_id INTEGER,
                team2_id INTEGER,
                match_points_team1 REAL,
                match_points_team2 REAL,
                game_points_team1 REAL,
                game_points_team2 REAL,
                FOREIGN KEY (tournament_id) REFERENCES Tournaments(id),
                FOREIGN KEY (team1_id) REFERENCES Teams(id),
                FOREIGN KEY (team2_id) REFERENCES Teams(id)
            )
        """)

        # TeamMatchGames table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS TeamMatchGames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_match_id INTEGER,
                board_number INTEGER,
                player1_id INTEGER,
                player2_id INTEGER,
                result_player1 REAL,
                result_player2 REAL,
                FOREIGN KEY (team_match_id) REFERENCES TeamMatches(id),
                FOREIGN KEY (player1_id) REFERENCES Players(id),
                FOREIGN KEY (player2_id) REFERENCES Players(id)
            )
        """)

        # Tournaments table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_date TEXT,
                number_of_rounds INTEGER,
                pairing_system TEXT,
                is_team_tournament BOOLEAN DEFAULT FALSE,
                boards_per_match INTEGER DEFAULT 4
            )
        """)

        # Rounds table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER,
                round_number INTEGER,
                FOREIGN KEY (tournament_id) REFERENCES Tournaments(id)
            )
        """)

        # Results table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id INTEGER,
                player1_id INTEGER,
                player2_id INTEGER, -- Allows NULL for byes
                player1_color TEXT,
                player2_color TEXT,
                winner_id INTEGER,  -- Allows 0 for draws, no foreign key
                is_bye BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (round_id) REFERENCES Rounds(id),
                FOREIGN KEY (player1_id) REFERENCES Players(id),
                FOREIGN KEY (player2_id) REFERENCES Players(id)
            )
        """)

        # TeamResults table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS TeamResults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id INTEGER,
                team1_id INTEGER,
                team2_id INTEGER,
                winner_id INTEGER,
                is_bye BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (round_id) REFERENCES Rounds(id),
                FOREIGN KEY (team1_id) REFERENCES Teams(id),
                FOREIGN KEY (team2_id) REFERENCES Teams(id),
                FOREIGN KEY (winner_id) REFERENCES Teams(id)
            )
        """)

        # PairingSystems table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS PairingSystems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT
            )
        """)

        # FloatHistory table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS FloatHistory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER,
                round_number INTEGER,
                player_id INTEGER,
                float_type TEXT, -- 'upfloat' or 'downfloat'
                FOREIGN KEY (tournament_id) REFERENCES Tournaments(id),
                FOREIGN KEY (player_id) REFERENCES Players(id)
            )
        """)

        # Indexes for optimization
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_tournament_id ON Players(tournament_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_rounds_tournament_id ON Rounds(tournament_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_round_id ON Results(round_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_player1_id ON Results(player1_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_player2_id ON Results(player2_id)")

        self.connection.commit()

    def _migrate_schema(self):
        """Handle schema migrations for existing databases."""
        # Check if pairing_number column exists in Players
        self.cursor.execute("PRAGMA table_info(Players)")
        columns = [info[1] for info in self.cursor.fetchall()]
        if "pairing_number" not in columns:
            try:
                print("Migrating schema: Adding pairing_number to Players table")
                self.cursor.execute("ALTER TABLE Players ADD COLUMN pairing_number INTEGER")
                self.connection.commit()
            except sqlite3.OperationalError as e:
                print(f"Migration error (might already exist): {e}")

        # Check if boards_per_match exists in Tournaments
        self.cursor.execute("PRAGMA table_info(Tournaments)")
        columns = [info[1] for info in self.cursor.fetchall()]
        if "boards_per_match" not in columns:
            try:
                print("Migrating schema: Adding boards_per_match to Tournaments table")
                self.cursor.execute("ALTER TABLE Tournaments ADD COLUMN boards_per_match INTEGER DEFAULT 4")
                self.connection.commit()
            except sqlite3.OperationalError as e:
                print(f"Migration error (might already exist): {e}")

        # Check if seed_ranking exists in Teams
        self.cursor.execute("PRAGMA table_info(Teams)")
        columns = [info[1] for info in self.cursor.fetchall()]
        if "seed_ranking" not in columns:
            try:
                print("Migrating schema: Adding seed_ranking and average_rating to Teams table")
                self.cursor.execute("ALTER TABLE Teams ADD COLUMN seed_ranking INTEGER")
                self.cursor.execute("ALTER TABLE Teams ADD COLUMN average_rating INTEGER")
                self.connection.commit()
            except sqlite3.OperationalError as e:
                print(f"Migration error (might already exist): {e}")

        # Rename board_number to board_order in TeamPlayers if it exists
        self.cursor.execute("PRAGMA table_info(TeamPlayers)")
        columns = [info[1] for info in self.cursor.fetchall()]
        if "board_number" in columns and "board_order" not in columns:
            try:
                print("Migrating schema: Renaming board_number to board_order in TeamPlayers")
                self.cursor.execute("ALTER TABLE TeamPlayers RENAME COLUMN board_number TO board_order")
                self.connection.commit()
            except sqlite3.OperationalError as e:
                print(f"Migration error: {e}")

    def add_player(self, name: str, elo: int, tournament_id: int, fide_id: str = None, federation: str = "UNK") -> int:
        """Add a player to the database."""
        self.cursor.execute(
            "INSERT INTO Players (name, elo, tournament_id, fide_id, federation) VALUES (?, ?, ?, ?, ?)",
            (name, elo, tournament_id, fide_id, federation)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def add_team(self, name: str, tournament_id: int, seed_ranking: int = None, average_rating: int = None) -> int:
        """Add a team to the database."""
        self.cursor.execute(
            "INSERT INTO Teams (name, tournament_id, seed_ranking, average_rating) VALUES (?, ?, ?, ?)",
            (name, tournament_id, seed_ranking, average_rating)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def add_team_player(self, team_id: int, player_id: int, board_order: int) -> int:
        """Add a player to a team."""
        self.cursor.execute(
            "INSERT INTO TeamPlayers (team_id, player_id, board_order) VALUES (?, ?, ?)",
            (team_id, player_id, board_order)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def add_tournament(self, name: str, start_date: str, number_of_rounds: int, 
                      pairing_system: str, is_team_tournament: bool, boards_per_match: int = 4) -> int:
        """Add a tournament to the database."""
        self.cursor.execute(
            "INSERT INTO Tournaments (name, start_date, number_of_rounds, pairing_system, is_team_tournament, boards_per_match) VALUES (?, ?, ?, ?, ?, ?)",
            (name, start_date, number_of_rounds, pairing_system, is_team_tournament, boards_per_match)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def add_round(self, tournament_id: int, round_number: int) -> int:
        """Add a round to the database."""
        self.cursor.execute(
            "INSERT INTO Rounds (tournament_id, round_number) VALUES (?, ?)",
            (tournament_id, round_number)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def add_result(self, round_id: int, player1_id: int, player2_id: Optional[int],
                   player1_color: Optional[str], player2_color: Optional[str], winner_id: Optional[int], is_bye: bool) -> int:
        """Add a result to the database."""
        self.cursor.execute(
            "INSERT INTO Results (round_id, player1_id, player2_id, player1_color, player2_color, winner_id, is_bye) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (round_id, player1_id, player2_id, player1_color, player2_color, winner_id, is_bye)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def add_team_result(self, round_id: int, team1_id: int, team2_id: int, 
                        winner_id: Optional[int], is_bye: bool) -> int:
        """Add a team result to the database."""
        self.cursor.execute(
            "INSERT INTO TeamResults (round_id, team1_id, team2_id, winner_id, is_bye) VALUES (?, ?, ?, ?, ?)",
            (round_id, team1_id, team2_id, winner_id, is_bye)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def get_players(self, tournament_id: int) -> List[Dict]:
        """Get all players for a tournament."""
        self.cursor.execute(
            "SELECT id, name, elo, tournament_id, fide_id, federation, withdrawn, pairing_number FROM Players WHERE tournament_id = ?",
            (tournament_id,)
        )
        rows = self.cursor.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "elo": row[2],
                "tournament_id": row[3],
                "fide_id": row[4],
                "federation": row[5],
                "withdrawn": row[6],
                "pairing_number": row[7],
                "score": 0,
                "tpn": row[4]
            }
            for row in rows
        ]

    def update_player_pairing_number(self, player_id: int, pairing_number: int):
        """Update the pairing number for a player."""
        self.cursor.execute(
            "UPDATE Players SET pairing_number = ? WHERE id = ?",
            (pairing_number, player_id)
        )
        self.connection.commit()

    def get_teams(self, tournament_id: int) -> List[Dict]:
        """Get all teams for a tournament with their current scores."""
        # Use a join to get match points and game points from TeamMatches
        # Sum them up for each team
        query = """
            SELECT 
                t.id, t.name, t.tournament_id, t.seed_ranking, t.average_rating,
                COALESCE(SUM(CASE WHEN tm.team1_id = t.id THEN tm.match_points_team1 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN tm.team2_id = t.id THEN tm.match_points_team2 ELSE 0 END), 0) as total_match_points,
                COALESCE(SUM(CASE WHEN tm.team1_id = t.id THEN tm.game_points_team1 ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN tm.team2_id = t.id THEN tm.game_points_team2 ELSE 0 END), 0) as total_game_points
            FROM Teams t
            LEFT JOIN TeamMatches tm ON (t.id = tm.team1_id OR t.id = tm.team2_id)
            WHERE t.tournament_id = ?
            GROUP BY t.id
        """
        self.cursor.execute(query, (tournament_id,))
        rows = self.cursor.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "tournament_id": row[2],
                "seed_ranking": row[3],
                "average_rating": row[4],
                "score": row[5],         # Match Points
                "game_points": row[6],   # Game Points
                "tpn": row[0]
            }
            for row in rows
        ]

    def get_team_players(self, team_id: int) -> List[Dict]:
        """Get all players for a team."""
        self.cursor.execute(
            "SELECT * FROM TeamPlayers WHERE team_id = ?",
            (team_id,)
        )
        rows = self.cursor.fetchall()
        return [
            {
                "id": row[0],
                "team_id": row[1],
                "player_id": row[2],
                "board_order": row[3]
            }
            for row in rows
        ]

    def get_tournaments(self) -> List[Dict]:
        """Get all tournaments."""
        self.cursor.execute("SELECT * FROM Tournaments")
        rows = self.cursor.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "start_date": row[2],
                "number_of_rounds": row[3],
                "pairing_system": row[4],
                "is_team_tournament": row[5]
            }
            for row in rows
        ]

    def get_rounds(self, tournament_id: int) -> List[Dict]:
        """Get all rounds for a tournament."""
        self.cursor.execute(
            "SELECT * FROM Rounds WHERE tournament_id = ?",
            (tournament_id,)
        )
        rows = self.cursor.fetchall()
        return [
            {
                "id": row[0],
                "tournament_id": row[1],
                "round_number": int(row[2])
            }
            for row in rows
        ]

    def get_results(self, round_id: int) -> List[Dict]:
        """Get all results for a round."""
        self.cursor.execute(
            "SELECT * FROM Results WHERE round_id = ?",
            (round_id,)
        )
        rows = self.cursor.fetchall()
        return [
            {
                "id": row[0],
                "round_id": row[1],
                "player1_id": row[2],
                "player2_id": row[3],
                "player1_color": row[4],
                "player2_color": row[5],
                "winner_id": row[6],
                "is_bye": row[7]
            }
            for row in rows
        ]

    def update_result(self, result_id: int, winner_id: Optional[int]) -> bool:
        """Update the winner for a game result in the database."""
        print(f"[Database.update_result] Updating result_id: {result_id} with winner_id: {winner_id}")
        self.cursor.execute(
            "UPDATE Results SET winner_id = ? WHERE id = ?",
            (winner_id, result_id)
        )
        self.connection.commit()
        return self.cursor.rowcount > 0

    def get_team_results(self, round_id: int) -> List[Dict]:
        """Get all team results for a round."""
        self.cursor.execute(
            "SELECT * FROM TeamResults WHERE round_id = ?",
            (round_id,)
        )
        rows = self.cursor.fetchall()
        return [
            {
                "id": row[0],
                "round_id": row[1],
                "team1_id": row[2],
                "team2_id": row[3],
                "winner_id": row[4],
                "is_bye": row[5]
            }
            for row in rows
        ]

    def get_player_color_history(self, tournament_id: int, player_id: int) -> List[str]:
        """Get the color history for a player in a tournament."""
        self.cursor.execute("""
            SELECT res.player1_color
            FROM Results res
            JOIN Rounds r ON res.round_id = r.id
            WHERE r.tournament_id = ? AND res.player1_id = ?
        """, (tournament_id, player_id))
        history1 = [row[0] for row in self.cursor.fetchall() if row[0]]

        self.cursor.execute("""
            SELECT res.player2_color
            FROM Results res
            JOIN Rounds r ON res.round_id = r.id
            WHERE r.tournament_id = ? AND res.player2_id = ?
        """, (tournament_id, player_id))
        history2 = [row[0] for row in self.cursor.fetchall() if row[0]]

        # This is a simplified representation. A more detailed history might be needed.
        return history1 + history2

    def get_players_with_bye(self, tournament_id: int) -> List[int]:
        """Get a list of player IDs who have received a bye in a tournament."""
        self.cursor.execute("""
            SELECT res.player1_id
            FROM Results res
            JOIN Rounds r ON res.round_id = r.id
            WHERE r.tournament_id = ? AND res.is_bye = 1
        """, (tournament_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def get_tournament_settings(self, tournament_id: int) -> Dict:
        """Get tournament settings."""
        # This is a placeholder. In a real application, this would fetch settings
        # from a dedicated table.
        return {"initial_color": "W"}

    def add_float_history(self, tournament_id: int, round_number: int, player_id: int, float_type: str):
        """Add a float history record for a player."""
        self.cursor.execute("""
            INSERT INTO FloatHistory (tournament_id, round_number, player_id, float_type)
            VALUES (?, ?, ?, ?)
        """, (tournament_id, round_number, player_id, float_type))
        self.connection.commit()

    def add_float_history_batch(self, history_data: List[Tuple]):
        """
        Add multiple float history records in a batch.
        Args:
            history_data: List of tuples (tournament_id, round_number, player_id, float_type)
        """
        self.cursor.executemany("""
            INSERT INTO FloatHistory (tournament_id, round_number, player_id, float_type)
            VALUES (?, ?, ?, ?)
        """, history_data)
        self.connection.commit()

    def get_player_float_history(self, tournament_id: int, player_id: int, float_type: str) -> List[int]:
        """Get the float history for a player."""
        self.cursor.execute("""
            SELECT round_number
            FROM FloatHistory
            WHERE tournament_id = ? AND player_id = ? AND float_type = ?
        """, (tournament_id, player_id, float_type))
        return [row[0] for row in self.cursor.fetchall()]

    def get_all_tournament_results(self, tournament_id: int) -> List[Dict]:
        """
        Get all results for a tournament efficiently using a JOIN.
        Returns a list of result dictionaries.
        """
        self.cursor.execute("""
            SELECT res.*
            FROM Results res
            JOIN Rounds r ON res.round_id = r.id
            WHERE r.tournament_id = ?
        """, (tournament_id,))
        
        rows = self.cursor.fetchall()
        return [
            {
                "id": row[0],
                "round_id": row[1],
                "player1_id": row[2],
                "player2_id": row[3],
                "player1_color": row[4],
                "player2_color": row[5],
                "winner_id": row[6],
                "is_bye": row[7]
            }
            for row in rows
        ]


    def close(self):
        """Close the database connection."""
        self.connection.close()