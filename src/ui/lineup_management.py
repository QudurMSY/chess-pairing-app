
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt

class LineupDialog(QDialog):
    """Dialog for selecting the lineup for a specific match."""

    def __init__(self, match, round_manager, team_manager, boards_per_match, parent=None):
        super().__init__(parent)
        self.match = match
        self.round_manager = round_manager
        self.team_manager = team_manager
        self.boards_per_match = boards_per_match
        
        # Load match teams
        self.round_manager.db.cursor.execute("SELECT name FROM Teams WHERE id = ?", (self.match['team1_id'],))
        self.t1_name = self.round_manager.db.cursor.fetchone()[0]
        self.round_manager.db.cursor.execute("SELECT name FROM Teams WHERE id = ?", (self.match['team2_id'],))
        self.t2_name = self.round_manager.db.cursor.fetchone()[0]
        
        self.init_ui()
        self.load_lineups()

    def init_ui(self):
        self.setWindowTitle(f"Edit Lineup: {self.t1_name} vs {self.t2_name}")
        self.setMinimumSize(800, 500)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Select active players for each board. Relative board order must be preserved."))

        # Tables for both teams
        tables_layout = QHBoxLayout()
        
        # Team 1
        t1_layout = QVBoxLayout()
        t1_layout.addWidget(QLabel(f"{self.t1_name} (White on B1)"))
        self.t1_table = QTableWidget(self.boards_per_match, 2)
        self.t1_table.setHorizontalHeaderLabels(["Board", "Player"])
        self.t1_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t1_layout.addWidget(self.t1_table)
        tables_layout.addLayout(t1_layout)
        
        # Team 2
        t2_layout = QVBoxLayout()
        t2_layout.addWidget(QLabel(f"{self.t2_name}"))
        self.t2_table = QTableWidget(self.boards_per_match, 2)
        self.t2_table.setHorizontalHeaderLabels(["Board", "Player"])
        self.t2_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t2_layout.addWidget(self.t2_table)
        tables_layout.addLayout(t2_layout)
        
        layout.addLayout(tables_layout)

        # Buttons
        btns = QHBoxLayout()
        save_btn = QPushButton("Save Lineups")
        save_btn.clicked.connect(self.save_lineups)
        save_btn.setStyleSheet("background-color: #007bff; color: white;")
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def load_lineups(self):
        # Fetch squad members for both teams
        self.t1_squad = self.team_manager.get_team_players(self.match['team1_id'])
        self.t2_squad = self.team_manager.get_team_players(self.match['team2_id'])
        
        # Fetch current games if they exist
        self.round_manager.db.cursor.execute(
            "SELECT board_number, player1_id, player2_id FROM TeamMatchGames WHERE team_match_id = ? ORDER BY board_number",
            (self.match['id'],)
        )
        games = {row[0]: (row[1], row[2]) for row in self.round_manager.db.cursor.fetchall()}
        
        self._fill_team_table(self.t1_table, self.t1_squad, 1, games)
        self._fill_team_table(self.t2_table, self.t2_squad, 2, games)

    def _fill_team_table(self, table, squad, team_idx, current_games):
        squad.sort(key=lambda x: x['board_order'])
        
        # Prepare squad names/ids for combos
        player_options = [("None / Absent", None)]
        for sq in squad:
            self.round_manager.db.cursor.execute("SELECT name, elo FROM Players WHERE id = ?", (sq['player_id'],))
            p_row = self.round_manager.db.cursor.fetchone()
            name = f"{p_row[0]} ({p_row[1]}) [B{sq['board_order']}]"
            player_options.append((name, sq['player_id']))

        for i in range(self.boards_per_match):
            board_num = i + 1
            table.setItem(i, 0, QTableWidgetItem(f"Board {board_num}"))
            
            combo = QComboBox()
            for name, pid in player_options:
                combo.addItem(name, pid)
            
            # Set current selection
            current_pid = None
            if board_num in current_games:
                current_pid = current_games[board_num][team_idx-1]
            elif i < len(squad):
                current_pid = squad[i]['player_id'] # Default to board order
                
            index = combo.findData(current_pid)
            if index != -1:
                combo.setCurrentIndex(index)
                
            table.setCellWidget(i, 1, combo)

    def save_lineups(self):
        # Validate board order and presence
        t1_lineup = self._get_table_lineup(self.t1_table)
        t2_lineup = self._get_table_lineup(self.t2_table)
        
        # Check if relative order is preserved for Team 1
        if not self._validate_lineup(t1_lineup, self.t1_squad):
            QMessageBox.warning(self, "Invalid Lineup", f"Relative board order must be preserved for {self.t1_name}.")
            return
            
        # Check if relative order is preserved for Team 2
        if not self._validate_lineup(t2_lineup, self.t2_squad):
            QMessageBox.warning(self, "Invalid Lineup", f"Relative board order must be preserved for {self.t2_name}.")
            return

        # Save to DB
        # 1. Clear existing (or update)
        self.round_manager.db.cursor.execute("DELETE FROM TeamMatchGames WHERE team_match_id = ?", (self.match['id'],))
        
        for i in range(self.boards_per_match):
            p1 = t1_lineup[i] if i < len(t1_lineup) else None
            p2 = t2_lineup[i] if i < len(t2_lineup) else None
            
            self.round_manager.db.cursor.execute(
                "INSERT INTO TeamMatchGames (team_match_id, board_number, player1_id, player2_id) VALUES (?, ?, ?, ?)",
                (self.match['id'], i+1, p1, p2)
            )
            
        self.round_manager.db.connection.commit()
        self.accept()

    def _get_table_lineup(self, table):
        lineup = []
        for i in range(self.boards_per_match):
            combo = table.cellWidget(i, 1)
            pid = combo.currentData()
            if pid:
                lineup.append(pid)
        return lineup

    def _validate_lineup(self, selected_pids, squad):
        if not selected_pids:
            return True # Should probably warn, but technically valid?
            
        # Get board orders for selected IDs
        orders = []
        squad_map = {s['player_id']: s['board_order'] for s in squad}
        for pid in selected_pids:
            orders.append(squad_map[pid])
            
        # Check if orders are strictly increasing
        return all(orders[i] < orders[i+1] for i in range(len(orders)-1))
