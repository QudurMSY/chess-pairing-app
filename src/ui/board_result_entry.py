
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QComboBox
)
from PyQt5.QtCore import Qt

class BoardResultDialog(QDialog):
    """Dialog for entering board-level results for a team match."""

    def __init__(self, match, round_manager, team_manager, boards_per_match, parent=None):
        super().__init__(parent)
        self.match = match
        self.round_manager = round_manager
        self.team_manager = team_manager
        self.boards_per_match = boards_per_match
        self.init_ui()
        self.load_boards()

    def init_ui(self):
        self.setWindowTitle("Enter Board Results")
        self.setMinimumSize(700, 500)
        layout = QVBoxLayout(self)

        # Team names
        self.round_manager.db.cursor.execute("SELECT name FROM Teams WHERE id = ?", (self.match['team1_id'],))
        t1_name = self.round_manager.db.cursor.fetchone()[0]
        self.round_manager.db.cursor.execute("SELECT name FROM Teams WHERE id = ?", (self.match['team2_id'],))
        t2_name = self.round_manager.db.cursor.fetchone()[0]

        layout.addWidget(QLabel(f"Match: {t1_name} vs {t2_name}"))

        # Boards table
        self.boards_table = QTableWidget(self.boards_per_match, 4)
        self.boards_table.setHorizontalHeaderLabels([
            f"Board", f"{t1_name} (White on B1)", f"{t2_name}", "Result"
        ])
        self.boards_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.boards_table)

        # Buttons
        btns = QHBoxLayout()
        save_btn = QPushButton("Save All Boards")
        save_btn.clicked.connect(self.save_results)
        save_btn.setStyleSheet("background-color: #28a745; color: white;")
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def load_boards(self):
        """Initializes boards and loads existing results if any."""
        # 1. Ensure TeamMatchGames exists for this match
        self.round_manager.db.cursor.execute(
            "SELECT * FROM TeamMatchGames WHERE team_match_id = ? ORDER BY board_number",
            (self.match['id'],)
        )
        games = self.round_manager.db.cursor.fetchall()
        
        if not games:
            # Initialize games if they don't exist
            # Get default lineups
            t1_players = self.team_manager.get_team_players(self.match['team1_id'])
            t2_players = self.team_manager.get_team_players(self.match['team2_id'])
            
            t1_players.sort(key=lambda x: x['board_order'])
            t2_players.sort(key=lambda x: x['board_order'])
            
            for i in range(1, self.boards_per_match + 1):
                p1_id = t1_players[i-1]['player_id'] if i <= len(t1_players) else None
                p2_id = t2_players[i-1]['player_id'] if i <= len(t2_players) else None
                
                self.round_manager.db.cursor.execute(
                    "INSERT INTO TeamMatchGames (team_match_id, board_number, player1_id, player2_id) VALUES (?, ?, ?, ?)",
                    (self.match['id'], i, p1_id, p2_id)
                )
            self.round_manager.db.connection.commit()
            
            # Re-fetch
            self.round_manager.db.cursor.execute(
                "SELECT * FROM TeamMatchGames WHERE team_match_id = ? ORDER BY board_number",
                (self.match['id'],)
            )
            games = self.round_manager.db.cursor.fetchall()

        # Fill table
        for i, game in enumerate(games):
            # game = (id, team_match_id, board_number, p1_id, p2_id, res1, res2)
            board_num = game[2]
            p1_id = game[3]
            p2_id = game[4]
            res1 = game[5]
            
            # Fetch names
            p1_name = "N/A"
            if p1_id:
                self.round_manager.db.cursor.execute("SELECT name FROM Players WHERE id = ?", (p1_id,))
                p1_name = self.round_manager.db.cursor.fetchone()[0]
                
            p2_name = "N/A"
            if p2_id:
                self.round_manager.db.cursor.execute("SELECT name FROM Players WHERE id = ?", (p2_id,))
                p2_name = self.round_manager.db.cursor.fetchone()[0]
            
            self.boards_table.setItem(i, 0, QTableWidgetItem(f"Board {board_num}"))
            self.boards_table.setItem(i, 1, QTableWidgetItem(p1_name))
            self.boards_table.setItem(i, 2, QTableWidgetItem(p2_name))
            
            combo = QComboBox()
            combo.addItem("Pending", None)
            combo.addItem("1-0", (1.0, 0.0))
            combo.addItem("0.5-0.5", (0.5, 0.5))
            combo.addItem("0-1", (0.0, 1.0))
            
            # Set current index
            if res1 == 1.0: combo.setCurrentIndex(1)
            elif res1 == 0.5: combo.setCurrentIndex(2)
            elif res1 == 0.0 and game[6] == 1.0: combo.setCurrentIndex(3)
            
            self.boards_table.setCellWidget(i, 3, combo)
            self.boards_table.item(i, 0).setData(Qt.UserRole, game[0]) # Store TeamMatchGame ID

    def save_results(self):
        """Saves all board results and aggregates them to the match level."""
        board_results = []
        
        for i in range(self.boards_per_match):
            # We assume rows correspond to board numbers 1..N
            board_num = i + 1
            combo = self.boards_table.cellWidget(i, 3)
            result = combo.currentData() # (score1, score2) or None
            
            p1_score = result[0] if result else None
            p2_score = result[1] if result else None
            
            board_results.append((board_num, p1_score, p2_score))
            
        # Use RoundManager to handle updates and score calculation
        self.round_manager.update_team_match_results_batch(self.match['id'], board_results)
        
        self.accept()
