
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel,
    QHeaderView, QHBoxLayout, QMessageBox, QComboBox
)
from PyQt5.QtCore import Qt


class SquadManagementDialog(QDialog):
    """Dialog for managing a team's squad (players and board order)."""

    def __init__(self, team, team_manager, player_manager, boards_per_match, parent=None):
        super().__init__(parent)
        self.team = team
        self.team_manager = team_manager
        self.player_manager = player_manager
        self.boards_per_match = boards_per_match
        self.init_ui()
        self.refresh_squad()

    def init_ui(self):
        self.setWindowTitle(f"Manage Squad: {self.team['name']}")
        self.setMinimumSize(600, 500)
        layout = QVBoxLayout(self)

        # Add player form
        add_group = QGroupBox("Add Player to Squad")
        add_layout = QFormLayout(add_group)
        
        self.name_input = QLineEdit()
        self.elo_input = QLineEdit()
        self.elo_input.setPlaceholderText("0")
        
        self.add_btn = QPushButton("Add Player")
        self.add_btn.clicked.connect(self._add_player)
        
        add_layout.addRow("Name:", self.name_input)
        add_layout.addRow("Elo:", self.elo_input)
        add_layout.addRow(self.add_btn)
        
        layout.addWidget(add_group)

        # Squad Table
        layout.addWidget(QLabel("Current Squad (Sorted by Board Order):"))
        self.squad_table = QTableWidget(0, 3)
        self.squad_table.setHorizontalHeaderLabels(["Board", "Name", "Elo"])
        self.squad_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.squad_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.squad_table)

        # Actions
        actions_layout = QHBoxLayout()
        
        self.reorder_btn = QPushButton("🔃 Auto-Reorder (by Elo)")
        self.reorder_btn.clicked.connect(self._reorder_squad)
        actions_layout.addWidget(self.reorder_btn)
        
        self.remove_btn = QPushButton("🗑️ Remove Selected")
        self.remove_btn.clicked.connect(self._remove_player)
        actions_layout.addWidget(self.remove_btn)
        
        layout.addLayout(actions_layout)

        # OK Button
        btns = QHBoxLayout()
        ok_btn = QPushButton("Close")
        ok_btn.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

    def refresh_squad(self):
        """Fetch and display team players."""
        self.squad_table.setRowCount(0)
        players = self.team_manager.get_team_players(self.team['id'])
        
        # Sort by board order
        players.sort(key=lambda x: x['board_order'])
        
        for i, tp in enumerate(players):
            # Fetch player details
            self.player_manager.db.cursor.execute(
                "SELECT name, elo FROM Players WHERE id = ?", (tp['player_id'],)
            )
            p_row = self.player_manager.db.cursor.fetchone()
            if p_row:
                name, elo = p_row
                row_idx = self.squad_table.rowCount()
                self.squad_table.insertRow(row_idx)
                
                board_item = QTableWidgetItem(str(tp['board_order']))
                board_item.setData(Qt.UserRole, tp['id']) # Store TeamPlayer ID
                
                self.squad_table.setItem(row_idx, 0, board_item)
                self.squad_table.setItem(row_idx, 1, QTableWidgetItem(name))
                self.squad_table.setItem(row_idx, 2, QTableWidgetItem(str(elo)))

    def _add_player(self):
        name = self.name_input.text().strip()
        elo_text = self.elo_input.text().strip()
        
        if not name:
            return
            
        try:
            elo = int(elo_text) if elo_text else 0
        except ValueError:
            QMessageBox.warning(self, "Error", "Elo must be a number.")
            return
            
        # 1. Create player in global pool (or tournament pool)
        player_id = self.player_manager.add_player(name, elo, self.team['tournament_id'])
        
        # 2. Add to team squad
        try:
            self.team_manager.add_player_to_team(self.team['id'], player_id)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Board Order", str(e))
            return
        
        # 3. Update team average rating
        self.team_manager.calculate_team_average_rating(self.team['id'], self.boards_per_match)
        
        self.name_input.clear()
        self.elo_input.clear()
        self.refresh_squad()

    def _reorder_squad(self):
        self.team_manager.reorder_team_players(self.team['id'])
        self.team_manager.calculate_team_average_rating(self.team['id'], self.boards_per_match)
        self.refresh_squad()
        QMessageBox.information(self, "Success", "Squad reordered by Elo and average rating updated.")

    def _remove_player(self):
        selected = self.squad_table.selectedItems()
        if not selected:
            return
            
        row = selected[0].row()
        tp_id = self.squad_table.item(row, 0).data(Qt.UserRole)
        
        # Delete from TeamPlayers
        self.player_manager.db.cursor.execute("DELETE FROM TeamPlayers WHERE id = ?", (tp_id,))
        self.player_manager.db.connection.commit()
        
        # Renumber remaining
        self.team_manager.reorder_team_players(self.team['id'])
        self.team_manager.calculate_team_average_rating(self.team['id'], self.boards_per_match)
        
        self.refresh_squad()
