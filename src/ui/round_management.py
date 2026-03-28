"""
Round management UI module for the Chess Pairing App.
This module defines the UI for round creation and result recording.
"""

import logging
from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QComboBox, QMessageBox,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QListWidgetItem
)
from PyQt5 import QtCore
from src.core.round_manager import RoundManager
from src.core.team_manager import TeamManager
from src.ui.board_result_entry import BoardResultDialog
from src.ui.lineup_management import LineupDialog

# Set up logging
# logging.basicConfig(level=logging.DEBUG) # Removed as global config is in main.py
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Explicitly set level for this module


class RoundManagementUI(QWidget):
    """UI for round creation and result recording."""

    def __init__(self, round_manager: RoundManager, team_manager: TeamManager = None):
        super().__init__()
        logger.info("RoundManagementUI __init__ called")
        logger.debug(f"Round manager instance: {round_manager}")
        self.round_manager = round_manager
        self.team_manager = team_manager
        self.current_result_id = None # To store the ID of the result being edited/updated
        self.is_team_tournament = False
        self.boards_per_match = 4
        self.init_ui()
        logger.info("RoundManagementUI initialization completed")

    def init_ui(self):
        """Initialize the UI components."""
        logger.info("RoundManagementUI init_ui called")
        layout = QVBoxLayout()
        
        # Tournament Info & Load
        info_layout = QHBoxLayout()
        self.tournament_label = QLabel("Tournament: Not Loaded")
        info_layout.addWidget(self.tournament_label)
        
        self.tournament_input = QLineEdit()
        self.tournament_input.setPlaceholderText("Tournament ID")
        self.tournament_input.setFixedWidth(100)
        info_layout.addWidget(self.tournament_input)
        
        load_tournament_btn = QPushButton("Load Tournament")
        load_tournament_btn.clicked.connect(self._load_tournament)
        info_layout.addWidget(load_tournament_btn)
        
        layout.addLayout(info_layout)

        # Round creation form
        create_group = QGroupBox("Round Control")
        create_layout = QHBoxLayout(create_group)
        
        round_number_label = QLabel("Round Number:")
        self.round_number_input = QLineEdit()
        self.round_number_input.setFixedWidth(50)
        
        create_button = QPushButton("Create Round")
        create_button.clicked.connect(self.create_round)
        
        create_layout.addWidget(round_number_label)
        create_layout.addWidget(self.round_number_input)
        create_layout.addWidget(create_button)
        
        layout.addWidget(create_group)
        
        # Result recording form
        self.individual_result_group = QGroupBox("Record Result (Individual)")
        result_form_layout = QHBoxLayout(self.individual_result_group)
        
        round_label = QLabel("Round ID:")
        self.round_input = QLineEdit()
        
        player1_label = QLabel("Player 1 ID:")
        self.player1_input = QLineEdit()
        
        player2_label = QLabel("Player 2 ID:")
        self.player2_input = QLineEdit()

        winner_label = QLabel("Result:")
        self.winner_combo = QComboBox()
        self.winner_combo.addItem("Pending", None)
        self.winner_combo.addItem("White Win", -1) # Placeholder
        self.winner_combo.addItem("Black Win", -1) # Placeholder
        self.winner_combo.addItem("Draw", 0)

        is_bye_label = QLabel("Is Bye:")
        self.is_bye_input = QComboBox()
        self.is_bye_input.addItems(["False", "True"])
        
        record_button = QPushButton("Record Result")
        record_button.clicked.connect(self.record_result)
        
        result_form_layout.addWidget(round_label)
        result_form_layout.addWidget(self.round_input)
        result_form_layout.addWidget(player1_label)
        result_form_layout.addWidget(self.player1_input)
        result_form_layout.addWidget(player2_label)
        result_form_layout.addWidget(self.player2_input)
        result_form_layout.addWidget(winner_label)
        result_form_layout.addWidget(self.winner_combo) # Use the QComboBox
        # Explanation for 'No Winner' vs 'Draw'
        explanation_label = QLabel("Pending = No result yet")
        explanation_label.setStyleSheet("font-size: 10px; color: gray;")
        result_form_layout.addWidget(explanation_label)
        result_form_layout.addWidget(is_bye_label)
        result_form_layout.addWidget(self.is_bye_input)
        result_form_layout.addWidget(record_button)
        
        layout.addWidget(self.individual_result_group)
        
        # Team Result Actions
        self.team_result_group = QGroupBox("Team Match Control")
        self.team_result_group.setVisible(False)
        team_layout = QHBoxLayout(self.team_result_group)
        
        self.edit_lineup_btn = QPushButton("📋 Edit Lineup")
        self.edit_lineup_btn.clicked.connect(self._edit_selected_lineup)
        
        self.enter_board_results_btn = QPushButton("🎲 Enter Board Results")
        self.enter_board_results_btn.clicked.connect(self._enter_selected_board_results)
        
        team_layout.addWidget(self.edit_lineup_btn)
        team_layout.addWidget(self.enter_board_results_btn)
        team_layout.addStretch()
        
        layout.addWidget(self.team_result_group)

        # Load games for round section
        load_games_layout = QHBoxLayout()
        round_id_label_refresh = QLabel("Round ID to Load:")
        self.round_id_input_refresh = QLineEdit()
        load_games_button = QPushButton("Load Games for Round")
        load_games_button.clicked.connect(self.load_games_for_round)

        load_games_layout.addWidget(round_id_label_refresh)
        load_games_layout.addWidget(self.round_id_input_refresh)
        load_games_layout.addWidget(load_games_button)
        layout.addLayout(load_games_layout)

        # Result list
        self.result_list = QListWidget()
        self.result_list.itemClicked.connect(self.load_result_into_form)
        self.result_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.result_list)

        self.setLayout(layout)
        logger.info("RoundManagementUI layout set")

        self._setup_winner_combo(None, None) # Initial setup for winner combo
        
        # Set window properties
        self.setWindowTitle("Round Management")
        self.resize(700, 500)
        logger.info("RoundManagementUI window properties set")

    def _load_tournament(self):
        try:
            tid_text = self.tournament_input.text()
            if not tid_text:
                return
            tid = int(tid_text)
            self.round_manager.db.cursor.execute(
                "SELECT name, is_team_tournament, boards_per_match FROM Tournaments WHERE id = ?", (tid,)
            )
            row = self.round_manager.db.cursor.fetchone()
            if row:
                name, is_team, boards = row
                self.is_team_tournament = bool(is_team)
                self.boards_per_match = boards or 4
                self.tournament_label.setText(f"Tournament: {name} ({'Team' if is_team else 'Individual'})")
                
                # Toggle UI elements
                self.individual_result_group.setVisible(not self.is_team_tournament)
                self.team_result_group.setVisible(self.is_team_tournament)
                
                # Try to load latest round ID
                rounds = self.round_manager.get_rounds(tid)
                if rounds:
                    self.round_id_input_refresh.setText(str(rounds[-1]['id']))
                    self.load_games_for_round()
            else:
                QMessageBox.warning(self, "Error", "Tournament not found")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid Tournament ID")

    def _on_item_double_clicked(self, item):
        if self.is_team_tournament:
            self._enter_selected_board_results()

    def _edit_selected_lineup(self):
        selected = self.result_list.selectedItems()
        if not selected:
            return
        match = selected[0].data(QtCore.Qt.UserRole)
        
        dialog = LineupDialog(match, self.round_manager, self.team_manager, self.boards_per_match, self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Success", "Lineup updated successfully.")
            self.load_games_for_round()

    def set_tournament(self, tournament_id: int):
        self.tournament_input.setText(str(tournament_id))
        self._load_tournament()

    def _enter_selected_board_results(self):
        selected = self.result_list.selectedItems()
        if not selected:
            return
        match = selected[0].data(QtCore.Qt.UserRole)
        
        dialog = BoardResultDialog(match, self.round_manager, self.team_manager, self.boards_per_match, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_games_for_round()

    def _setup_winner_combo(self, player1_id: Optional[int], player2_id: Optional[int]):
        self.winner_combo.clear()
        self.winner_combo.addItem("Pending", None)
        self.winner_combo.addItem("Draw", 0)
        if player1_id:
            self.winner_combo.addItem(f"White Win ({player1_id})", player1_id)
        if player2_id:
            self.winner_combo.addItem(f"Black Win ({player2_id})", player2_id)

    def _check_previous_round_completion_for_tournament(self, tournament_id, round_number):
        """Check if the previous round is complete before creating a new round."""
        try:
            # Get all rounds for the tournament
            rounds = self.round_manager.get_rounds(tournament_id)
            
            # If no rounds exist, allow first round creation
            if not rounds:
                return True, "No previous rounds to check."
            
            # Get the most recent round (last round)
            previous_round = rounds[-1]
            previous_round_number = previous_round["round_number"]
            
            # Only check if we're not creating the first round
            if round_number <= previous_round_number:
                return True, f"Round {round_number} is not after the last completed round."
            
            # Get results for the previous round
            results = self.round_manager.get_round_results(previous_round["id"])
            
            if not results:
                return False, f"No games found in round {previous_round_number}."
            
            # Count incomplete games (games without winner_id and not byes)
            incomplete_games = [r for r in results if r["winner_id"] is None and not r["is_bye"]]
            
            if incomplete_games:
                incomplete_count = len(incomplete_games)
                error_message = (
                    f"Cannot create round {round_number}: "
                    f"{incomplete_count} game(s) in round {previous_round_number} have no results.\n\n"
                    f"Please complete all games before creating the next round."
                )
                return False, error_message
            
            return True, f"All games in round {previous_round_number} are complete."
            
        except Exception as e:
            return False, f"Error checking round completion: {str(e)}"

    def create_round(self):
        """Create a new round."""
        try:
            tournament_id = int(self.tournament_input.text())
            round_number = int(self.round_number_input.text())
            
            # Check if previous round is complete
            is_complete, message = self._check_previous_round_completion_for_tournament(tournament_id, round_number)
            
            if not is_complete:
                QMessageBox.warning(self, "Round Completion Error", message)
                return
            
            round_id = self.round_manager.create_round(tournament_id, round_number)
            
            QMessageBox.information(self, "Success", f"Round created with ID: {round_id}")
            
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter valid numeric values for Tournament ID and Round Number.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create round: {str(e)}")
            logger.error(f"Error creating round: {e}")

    def record_result(self):
        """Record or update a game result."""
        try:
            round_id = int(self.round_input.text())
            player1_id = int(self.player1_input.text())
            player2_id = int(self.player2_input.text()) if self.player2_input.text() else None
            winner_id = self.winner_combo.currentData() # Get data from the combobox
            
            # Explicitly handle Draw case if data retrieval fails or returns None for 0
            if self.winner_combo.currentText() == "Draw" and winner_id is None:
                logger.warning("Selected 'Draw' but data is None. Forcing winner_id to 0.")
                winner_id = 0
                
            is_bye = self.is_bye_input.currentText() == "True"

            logger.debug(f"[record_result] current_result_id: {self.current_result_id}, winner_id from combo: {winner_id}")

            if self.current_result_id:
                # Retrieve previous result to check for confirmation dialog conditions
                previous_result = self.round_manager.get_result_by_id(self.current_result_id)
                previous_winner_id = previous_result["winner_id"] if previous_result else None

                # Check if user is attempting to clear a previously recorded result
                if winner_id is None and previous_winner_id is not None:
                    reply = QMessageBox.question(
                        self, "Confirm Clear Result",
                        "You are about to clear a previously recorded result. Are you sure you want to proceed?",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        logger.info("Clearing result cancelled by user.")
                        return # Abort the update

                # Update existing result
                logger.debug(f"[record_result] Updating result ID: {self.current_result_id} with winner_id: {winner_id}")
                print(f"[record_result] Updating result ID: {self.current_result_id} with winner_id: {winner_id} (Type: {type(winner_id)})")
                success = self.round_manager.update_result(self.current_result_id, winner_id)
                if success:
                    QMessageBox.information(self, "Success", f"Result for Game ID {self.current_result_id} updated.")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to update result for Game ID {self.current_result_id}.")
            else:
                # Record new result (this path might be less used if pairings are pre-created)
                logger.debug(f"[record_result] Recording new result for round_id: {round_id}, player1_id: {player1_id}, player2_id: {player2_id}, winner_id: {winner_id}, is_bye: {is_bye}")
                result_id = self.round_manager.record_result(
                    round_id, player1_id, player2_id, winner_id, is_bye
                )
                QMessageBox.information(self, "Success", f"Result recorded with ID: {result_id}")

            self.clear_result_form()
            self.load_games_for_round() # Refresh the list after recording/updating

        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter valid numeric values for player IDs and Round ID.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to record/update result: {str(e)}")
            logger.error(f"Error recording/updating result: {e}")

    def load_games_for_round(self):
        """Load and display all games for the specified round ID."""
        self.result_list.clear()
        try:
            round_id = int(self.round_id_input_refresh.text())
            results = self.round_manager.get_round_results(round_id)

            if not results:
                QMessageBox.information(self, "Info", f"No games found for Round ID {round_id}.")
                return
            
            for result in results:
                item_text = (
                    f"Game ID: {result["id"]}, P1: {result["player1_id"]}, P2: {result["player2_id"] or 'BYE'}, "
                    f"Winner: {'Draw' if result['winner_id'] == 0 else result['winner_id'] or 'Pending'}, Bye: {result['is_bye']}"
                )
                item = QListWidgetItem(item_text)
                item.setData(QtCore.Qt.UserRole, result)  # Store the full result dict in the item
                self.result_list.addItem(item)
            logger.info(f"Loaded {len(results)} games for Round ID {round_id}")

        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter a valid numeric value for Round ID to load.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load games: {str(e)}")
            logger.error(f"Error loading games: {e}")

    def load_result_into_form(self, item):
        """Load the details of a selected game into the result recording form."""
        result = item.data(QtCore.Qt.UserRole)
        if result:
            self.current_result_id = result["id"]
            self.round_input.setText(str(result["round_id"])) # Set the round_input field
            self.player1_input.setText(str(result["player1_id"]))
            self.player2_input.setText(str(result["player2_id"]) if result["player2_id"] else "")

            logger.debug(f"[load_result_into_form] Loading result ID: {self.current_result_id}, winner_id from DB: {result["winner_id"]}")

            self._setup_winner_combo(result["player1_id"], result["player2_id"])
            
            # Explicitly find and set the current index based on winner_id
            winner_id = result["winner_id"]
            index = self.winner_combo.findData(winner_id)

            # Robust check for 0 (Draw) if findData fails (e.g. due to strict type checking)
            if index == -1 and winner_id == 0:
                for i in range(self.winner_combo.count()):
                    # Check equality explicitly, allowing for type flexibility if needed
                    if self.winner_combo.itemData(i) == 0 and self.winner_combo.itemData(i) is not None:
                        index = i
                        break

            if index != -1:
                self.winner_combo.setCurrentIndex(index)
                logger.debug(f"[load_result_into_form] Set winner_combo to index {index} for winner_id {winner_id}")
            else:
                # Default to "Pending" if winner_id is not found (e.g., None, or unexpected value)
                self.winner_combo.setCurrentIndex(self.winner_combo.findData(None))
                logger.debug(f"[load_result_into_form] Defaulted winner_combo to Pending for result ID {self.current_result_id} (winner_id from DB: {winner_id})")

            self.is_bye_input.setCurrentText("True" if result["is_bye"] else "False")
            logger.info(f"Loaded game ID {self.current_result_id} into form.")

    def clear_result_form(self):
        """Clear the result input fields and reset current_result_id."""
        self.current_result_id = None
        self.round_input.clear()
        self.player1_input.clear()
        self.player2_input.clear()
        self.winner_combo.setCurrentIndex(self.winner_combo.findData(None)) # Reset to Pending
        self._setup_winner_combo(None, None) # Reset player IDs in combo
        self.is_bye_input.setCurrentIndex(0) # Set to False
        logger.info("Result form cleared.")
