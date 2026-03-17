"""
Player registration UI module for the Chess Pairing App.
This module defines the UI for player registration and management.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QMessageBox, QFileDialog,
    QComboBox, QGroupBox, QFormLayout, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from src.core.player_manager import PlayerManager
from src.core.team_manager import TeamManager
from src.ui.squad_management import SquadManagementDialog

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class PlayerRegistrationUI(QWidget):
    """UI for player registration and management."""

    def __init__(self, player_manager: PlayerManager, team_manager: TeamManager = None):
        super().__init__()
        logger.info("PlayerRegistrationUI __init__ called")
        self.player_manager = player_manager
        self.team_manager = team_manager
        self.current_tournament_id = None
        self.is_team_tournament = False
        self.init_ui()
        logger.info("PlayerRegistrationUI initialization completed")

    def init_ui(self):
        """Initialize the UI components."""
        logger.info("PlayerRegistrationUI init_ui called")
        layout = QVBoxLayout()
        
        # Tournament selection / Info
        tournament_info_layout = QHBoxLayout()
        self.tournament_label = QLabel("Tournament: Not Selected")
        tournament_info_layout.addWidget(self.tournament_label)
        
        # For standalone use/testing
        self.tournament_input = QLineEdit()
        self.tournament_input.setPlaceholderText("Enter Tournament ID")
        self.tournament_input.setFixedWidth(150)
        tournament_info_layout.addWidget(self.tournament_input)
        
        load_btn = QPushButton("Load Tournament")
        load_btn.clicked.connect(self._load_tournament_from_id)
        tournament_info_layout.addWidget(load_btn)
        
        layout.addLayout(tournament_info_layout)

        # --- Individual Player Registration (Hidden if team tournament) ---
        self.individual_group = QGroupBox("Register Player")
        form_layout = QHBoxLayout(self.individual_group)
        
        name_label = QLabel("Name:")
        self.name_input = QLineEdit()
        
        elo_label = QLabel("Elo:")
        self.elo_input = QLineEdit()
        
        register_button = QPushButton("Register Player")
        register_button.clicked.connect(self.register_player)
        
        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(elo_label)
        form_layout.addWidget(self.elo_input)
        form_layout.addWidget(register_button)
        
        layout.addWidget(self.individual_group)

        # --- Team Registration (Hidden if not team tournament) ---
        self.team_group = QGroupBox("Register Team")
        self.team_group.setVisible(False)
        team_form_layout = QHBoxLayout(self.team_group)
        
        team_name_label = QLabel("Team Name:")
        self.team_name_input = QLineEdit()
        
        register_team_button = QPushButton("Register Team")
        register_team_button.clicked.connect(self.register_team)
        
        team_form_layout.addWidget(team_name_label)
        team_form_layout.addWidget(self.team_name_input)
        team_form_layout.addWidget(register_team_button)
        
        layout.addWidget(self.team_group)
        
        # Player/Team list
        self.list_label = QLabel("Registered Players:")
        layout.addWidget(self.list_label)
        
        self.data_list = QListWidget()
        self.data_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.data_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_button = QPushButton("🔄 Refresh")
        refresh_button.clicked.connect(self.refresh_list)
        button_layout.addWidget(refresh_button)

        import_button = QPushButton("📁 Import from TXT")
        import_button.clicked.connect(self.import_players)
        button_layout.addWidget(import_button)
        
        self.manage_squad_btn = QPushButton("👥 Manage Squad")
        self.manage_squad_btn.setVisible(False)
        self.manage_squad_btn.clicked.connect(self._manage_selected_team_squad)
        button_layout.addWidget(self.manage_squad_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setWindowTitle("Registration Management")
        self.resize(700, 500)

    def _load_tournament_from_id(self):
        """Loads tournament details from the ID input."""
        try:
            tid_text = self.tournament_input.text()
            if not tid_text:
                return
            tid = int(tid_text)
            self.set_tournament(tid)
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid Tournament ID")

    def set_tournament(self, tournament_id: int):
        """Configures the UI for a specific tournament."""
        self.current_tournament_id = tournament_id
        
        # Fetch tournament details
        self.player_manager.db.cursor.execute(
            "SELECT name, is_team_tournament, boards_per_match FROM Tournaments WHERE id = ?",
            (tournament_id,)
        )
        row = self.player_manager.db.cursor.fetchone()
        if row:
            name, is_team, boards = row
            self.is_team_tournament = bool(is_team)
            self.boards_per_match = boards or 4
            self.tournament_label.setText(f"Tournament: {name} ({'Team' if is_team else 'Individual'})")
            self.tournament_input.setText(str(tournament_id))
            
            # Toggle UI groups
            self.individual_group.setVisible(not self.is_team_tournament)
            self.team_group.setVisible(self.is_team_tournament)
            self.manage_squad_btn.setVisible(self.is_team_tournament)
            self.list_label.setText("Registered Teams:" if self.is_team_tournament else "Registered Players:")
            
            self.refresh_list()
        else:
            QMessageBox.warning(self, "Error", f"Tournament ID {tournament_id} not found.")

    def register_player(self):
        """Register a new player."""
        if not self.current_tournament_id:
            QMessageBox.warning(self, "Error", "No tournament selected.")
            return
            
        name = self.name_input.text().strip()
        elo_text = self.elo_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Name is required.")
            return
            
        try:
            elo = int(elo_text) if elo_text else 0
        except ValueError:
            QMessageBox.warning(self, "Error", "Elo must be a number.")
            return
            
        player_id = self.player_manager.add_player(name, elo, self.current_tournament_id)
        logger.info(f"Registered player {name} with ID {player_id}")
        
        self.name_input.clear()
        self.elo_input.clear()
        self.refresh_list()

    def register_team(self):
        """Register a new team."""
        if not self.current_tournament_id or not self.team_manager:
            return
            
        name = self.team_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Team name is required.")
            return
            
        team_id = self.team_manager.add_team(name, self.current_tournament_id)
        logger.info(f"Registered team {name} with ID {team_id}")
        
        self.team_name_input.clear()
        self.refresh_list()

    def refresh_list(self, tournament_id=None):
        """Refresh the player/team list."""
        if tournament_id:
            self.current_tournament_id = tournament_id
            
        if not self.current_tournament_id:
            return
            
        self.data_list.clear()
        
        if self.is_team_tournament:
            teams = self.team_manager.get_teams(self.current_tournament_id)
            for team in teams:
                players = self.team_manager.get_team_players(team['id'])
                text = f"{team['name']} (Squad: {len(players)} players)"
                if team.get('average_rating'):
                    text += f" - Avg Elo: {team['average_rating']}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, team['id'])
                self.data_list.addItem(item)
        else:
            players = self.player_manager.get_players(self.current_tournament_id)
            for player in players:
                text = f"{player['name']} ({player['elo']})"
                if player.get('federation'):
                    text += f" [{player['federation']}]"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, player['id'])
                self.data_list.addItem(item)

    def _on_item_double_clicked(self, item):
        """Handle double-click on list item."""
        if self.is_team_tournament:
            self._manage_selected_team_squad()

    def _manage_selected_team_squad(self):
        """Opens the squad management dialog for the selected team."""
        selected_items = self.data_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Selection Required", "Please select a team to manage its squad.")
            return
            
        team_id = selected_items[0].data(Qt.UserRole)
        team = self.team_manager.get_team_by_id(team_id)
        
        if not team:
            return
            
        dialog = SquadManagementDialog(team, self.team_manager, self.player_manager, self.boards_per_match, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_list()

    def refresh_player_list(self, tournament_id=None):
        """Legacy method for compatibility."""
        self.refresh_list(tournament_id)

    def import_players(self):
        """Import players from a file."""
        logger.info("import_players called")
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Player File",
                "",
                "Text Files (*.txt)"
            )
            
            if not file_path:
                logger.info("Import cancelled by user")
                return
                
            logger.info(f"Selected file: {file_path}")
            result = self.player_manager.import_players_from_file(file_path)
            
            if result['success']:
                count = result['count']
                errors = result['errors']
                logger.info(f"File parsed successfully. Found {count} players.")

                if count == 0:
                    msg = "No valid players found in file."
                    if errors:
                        msg += "\n\nErrors encountered:\n" + "\n".join(errors[:5])
                        if len(errors) > 5:
                            msg += "\n..."
                    QMessageBox.warning(self, "Import Failed", msg)
                    return

                message = f"Successfully parsed {count} players from file."
                if errors:
                    message += f"\n\nEncountered {len(errors)} errors:\n" + "\n".join(errors[:5])
                    if len(errors) > 5:
                        message += "\n..."
                
                # If tournament ID is present, offer to add players to DB
                try:
                    tournament_id_text = self.tournament_input.text()
                    if not tournament_id_text:
                         QMessageBox.warning(
                            self,
                            "Tournament ID Required",
                            f"{message}\n\nPlease enter a Tournament ID to add players to the database."
                        )
                         return

                    tournament_id = int(tournament_id_text)
                    reply = QMessageBox.question(
                        self,
                        "Add to Tournament",
                        f"{message}\n\nDo you want to add these {count} players to Database for Tournament ID {tournament_id}?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        logger.info(f"User confirmed addition to tournament {tournament_id}")
                        added_count = 0
                        for player in result['players']:
                            try:
                                pid = self.player_manager.add_player(
                                    name=player['name'],
                                    elo=player['elo'],
                                    tournament_id=tournament_id,
                                    fide_id=player['fide_id'],
                                    federation=player['federation']
                                )
                                if pid:
                                    added_count += 1
                                else:
                                    logger.error(f"Failed to add player {player['name']}: add_player returned {pid}")
                            except Exception as e:
                                logger.error(f"Failed to add player {player['name']}: {e}")
                                
                        logger.info(f"Successfully added {added_count} players to DB")
                        
                        if added_count == 0:
                             QMessageBox.warning(self, "Import Warning", "No players were registered. Please check the logs for database errors.")
                        else:
                            success_msg = f"Successfully saved {added_count} players to the database for Tournament {tournament_id}."
                            if added_count < count:
                                success_msg += f"\n\nNote: {count - added_count} players failed to register."
                            QMessageBox.information(self, "Database Update", success_msg)
                            self.refresh_player_list(tournament_id=tournament_id)
                    else:
                        logger.info("User declined to add players to DB")
                        QMessageBox.warning(self, "Import Cancelled", "No players registered (cancelled by user).")
                        
                except ValueError:
                    # Invalid tournament ID format
                    QMessageBox.warning(
                        self,
                        "Invalid Tournament ID",
                        "Please enter a valid numeric Tournament ID."
                    )
                    
            else:
                logger.error(f"Import parsing failed: {result['errors']}")
                QMessageBox.warning(self, "Import Failed", "\n".join(result['errors']))

        except Exception as e:
            logger.exception("Unexpected error in import_players")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
            return