"""
Tournament Manager UI module for the Chess Pairing App.
This module defines the UI for managing existing tournaments, including round management and result entry.
"""

import logging
import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QComboBox, QMessageBox, QTabWidget, QTextEdit, QFormLayout, QSpinBox,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QGridLayout,
    QFrame, QScrollArea, QSplitter, QApplication, QFileDialog, QMenu, QDialog
)
from PyQt5.QtCore import Qt
from src.core.tournament_manager import TournamentManager
from src.core.player_manager import PlayerManager
from src.core.round_manager import RoundManager
from src.core.team_manager import TeamManager
from src.core.tie_break import TieBreak
from src.core.reporting import ReportGenerator
from src.ui.round_management import RoundManagementUI

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TournamentManagerUI(QWidget):
    """UI for managing existing tournaments."""

    def __init__(self, tournament_manager: TournamentManager, 
                 player_manager: PlayerManager, round_manager: RoundManager,
                 team_manager: TeamManager = None):
        super().__init__()
        logger.info("TournamentManagerUI __init__ called")
        
        self.tournament_manager = tournament_manager
        self.player_manager = player_manager
        self.round_manager = round_manager
        self.team_manager = team_manager
        self.tie_break = TieBreak(self.tournament_manager.db)
        self.report_generator = ReportGenerator(self.tournament_manager.db)
        self.current_tournament = None
        self.current_round = None
        
        self.init_ui()
        logger.info("TournamentManagerUI initialization completed")

    def init_ui(self):
        """Initialize the UI components."""
        logger.info("TournamentManagerUI init_ui called")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Stacked pages approach manually implemented with visibility toggling
        # Page 1: Tournament Selection
        self.selection_widget = self._create_selection_widget()
        self.main_layout.addWidget(self.selection_widget)
        
        # Page 2: Dashboard (Initially Hidden)
        self.dashboard_widget = self._create_dashboard_widget()
        self.dashboard_widget.setVisible(False)
        self.main_layout.addWidget(self.dashboard_widget)

    def _create_selection_widget(self):
        """Create the tournament selection screen."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Select a Tournament to Manage")
        title.setObjectName("managerTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.tournament_list = QListWidget()
        self.tournament_list.setMinimumWidth(400)
        self.tournament_list.setMaximumWidth(800) # Optional max width for aesthetics
        self.tournament_list.setFixedHeight(400)
        self.tournament_list.itemClicked.connect(self._load_selected_tournament)
        layout.addWidget(self.tournament_list, alignment=Qt.AlignCenter)
        
        refresh_btn = QPushButton("🔄 Refresh List")
        refresh_btn.setMinimumWidth(200)
        refresh_btn.setToolTip("Refresh the list of tournaments from the database")
        refresh_btn.clicked.connect(self._refresh_tournament_list)
        layout.addWidget(refresh_btn, alignment=Qt.AlignCenter)
        
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.setObjectName("dangerButton")
        delete_btn.setMinimumWidth(200)
        delete_btn.setToolTip("Permanently delete the selected tournament")
        delete_btn.clicked.connect(self._delete_selected_tournament)
        layout.addWidget(delete_btn, alignment=Qt.AlignCenter)
        
        return widget

    def _create_dashboard_widget(self):
        """Create the main dashboard for a selected tournament."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # --- Top Bar: Title & Navigation ---
        top_bar = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self._show_selection_screen)
        top_bar.addWidget(back_btn)
        
        self.tournament_title_label = QLabel("Tournament Name")
        self.tournament_title_label.setObjectName("tournamentTitle")
        top_bar.addWidget(self.tournament_title_label)
        top_bar.addStretch()
        layout.addLayout(top_bar)
        
        # --- Action Bar ---
        action_bar = QFrame()
        action_bar.setObjectName("actionBar")
        action_layout = QHBoxLayout(action_bar)
        
        self.generate_round_btn = QPushButton("Example Action") # Placeholder, set in logic
        self.generate_round_btn.setToolTip("Generate pairings for the next round")
        self.generate_round_btn.clicked.connect(self._generate_next_round)
        action_layout.addWidget(self.generate_round_btn)
        
        enter_results_btn = QPushButton("✏️ Enter Results")
        enter_results_btn.setToolTip("Switch to the results entry view")
        enter_results_btn.clicked.connect(self._switch_to_results_tab)
        action_layout.addWidget(enter_results_btn)
        
        add_player_btn = QPushButton("➕ Add Player")
        add_player_btn.setToolTip("Add a new player or team to the tournament")
        add_player_btn.clicked.connect(self._add_new_player)
        action_layout.addWidget(add_player_btn)
        
        export_btn = QPushButton("📥 Export Standings")
        export_btn.setToolTip("Export the current tournament standings")
        export_menu = QMenu(self)
        
        export_csv_action = export_menu.addAction("Export to CSV")
        export_csv_action.triggered.connect(lambda: self._export_standings("csv"))
        
        export_txt_action = export_menu.addAction("Export to Text")
        export_txt_action.triggered.connect(lambda: self._export_standings("txt"))
        
        export_btn.setMenu(export_menu)
        action_layout.addWidget(export_btn)
        
        action_layout.addStretch()
        layout.addWidget(action_bar)
        
        # --- Main Content: Tabs for Views ---
        self.content_tabs = QTabWidget()
        
        # Tab 1: Dashboard Overview (Split View)
        self.overview_tab = self._create_overview_tab()
        self.content_tabs.addTab(self.overview_tab, "📊 Dashboard")
        
        # Adjust standings table columns based on tournament type
        # We will update labels in _refresh_dashboard_data
        
        # Tab 2: Detailed Results / Pairings
        self.pairings_tab = self._create_pairings_tab()
        self.content_tabs.addTab(self.pairings_tab, "⚔️ Pairings & Results")
        
        # Tab 3: Players
        self.players_tab = self._create_players_tab()
        self.content_tabs.addTab(self.players_tab, "👥 Players")
        
        layout.addWidget(self.content_tabs)
        
        return widget

    def _create_overview_tab(self):
        """Create the dashboard overview tab."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left: Standings
        standings_group = QFrame()
        standings_layout = QVBoxLayout(standings_group)
        standings_layout.addWidget(QLabel("<b>Current Standings</b>"))
        
        self.standings_table = QTableWidget()
        self.standings_table.setColumnCount(4)
        self.standings_table.setHorizontalHeaderLabels(["Rank", "Name", "Score", "SB"])
        self.standings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.standings_table.verticalHeader().setDefaultSectionSize(50)
        standings_layout.addWidget(self.standings_table)
        
        layout.addWidget(standings_group, 1) # 50% width
        
        # Right: Recent Activity / Round Info
        right_group = QFrame()
        right_layout = QVBoxLayout(right_group)
        
        right_layout.addWidget(QLabel("<b>Round Status</b>"))
        self.round_status_label = QLabel("No rounds generated")
        right_layout.addWidget(self.round_status_label)
        
        right_layout.addWidget(QLabel("<b>Top Pairings (Current Round)</b>"))
        self.top_pairings_list = QListWidget()
        right_layout.addWidget(self.top_pairings_list)
        
        layout.addWidget(right_group, 1) # 50% width
        
        return widget

    def _create_pairings_tab(self):
        """Create detailed pairings and results tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Round Selector
        controls = QHBoxLayout()
        controls.addWidget(QLabel("View Round:"))
        self.round_combo = QComboBox()
        self.round_combo.setToolTip("Select round to view pairings and results")
        self.round_combo.currentIndexChanged.connect(self._load_selected_round)
        controls.addWidget(self.round_combo)
        
        export_pairings_btn = QPushButton("📥 Export Pairings")
        export_pairings_btn.setToolTip("Export pairings for the selected round")
        export_pairings_menu = QMenu(self)
        
        export_pairings_csv = export_pairings_menu.addAction("Export to CSV")
        export_pairings_csv.triggered.connect(lambda: self._export_pairings("csv"))
        
        export_pairings_txt = export_pairings_menu.addAction("Export to Text")
        export_pairings_txt.triggered.connect(lambda: self._export_pairings("txt"))
        
        export_pairings_btn.setMenu(export_pairings_menu)
        controls.addWidget(export_pairings_btn)

        controls.addStretch()
        layout.addLayout(controls)
        
        # Pairings Table
        self.pairings_table = QTableWidget()
        self.pairings_table.setColumnCount(5)
        self.pairings_table.setHorizontalHeaderLabels(["Board", "White", "Black", "Result", "Action"])
        self.pairings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pairings_table.verticalHeader().setDefaultSectionSize(50) # Ensure enough height for buttons
        layout.addWidget(self.pairings_table)
        
        return widget

    def _create_players_tab(self):
        """Create players management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.player_table = QTableWidget()
        self.player_table.setColumnCount(5)
        self.player_table.setHorizontalHeaderLabels(["ID", "Name", "Elo", "Fed", "Status"])
        self.player_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.player_table.verticalHeader().setDefaultSectionSize(50)
        layout.addWidget(self.player_table)
        
        actions = QHBoxLayout()
        withdraw_btn = QPushButton("Withdraw Selected")
        withdraw_btn.clicked.connect(self._withdraw_selected_player)
        actions.addWidget(withdraw_btn)
        actions.addStretch()
        layout.addLayout(actions)
        
        return widget

    # --- Navigation Logic ---

    def _show_selection_screen(self):
        self.dashboard_widget.setVisible(False)
        self.selection_widget.setVisible(True)
        self.current_tournament = None
        self._refresh_tournament_list()

    def _show_dashboard(self, tournament):
        self.current_tournament = tournament
        self.tournament_title_label.setText(f"{tournament['name']} (Rounds: {tournament['number_of_rounds']})")
        
        self.selection_widget.setVisible(False)
        self.dashboard_widget.setVisible(True)
        
        # Load Data
        self._load_rounds()
        self._load_players()
        self._refresh_dashboard_data()

    def _switch_to_results_tab(self):
        """Switch directly to the Pairings & Results tab."""
        self.content_tabs.setCurrentIndex(1)

    # --- Data Loading & Actions ---

    def _refresh_tournament_list(self):
        self.tournament_list.clear()
        tournaments = self.tournament_manager.get_tournaments()
        for t in tournaments:
            item = QListWidgetItem(f"{t['name']} - {t['start_date']}")
            item.setData(Qt.UserRole, t['id'])
            self.tournament_list.addItem(item)

    def _load_selected_tournament(self, item):
        t_id = item.data(Qt.UserRole)
        tournament = self.tournament_manager.get_tournament_by_id(t_id)
        if tournament:
            self._show_dashboard(tournament)

    def _delete_selected_tournament(self):
        selected = self.tournament_list.selectedItems()
        if not selected:
            return
        
        if QMessageBox.question(self, "Confirm", "Delete this tournament?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            t_id = selected[0].data(Qt.UserRole)
            self.tournament_manager.delete_tournament(t_id)
            self._refresh_tournament_list()

    def _refresh_dashboard_data(self):
        """Refresh standings and overview data."""
        if not self.current_tournament:
            return
            
        # Standings
        is_team = self.current_tournament.get("is_team_tournament", False)
        if is_team:
            self.standings_table.setHorizontalHeaderLabels(["Rank", "Team Name", "MP", "GP"])
            from src.core.team_manager import TeamManager
            team_manager = TeamManager(self.tournament_manager.db)
            teams = team_manager.get_teams(self.current_tournament['id'])
            # Sort by match points (desc), then game points (desc)
            teams.sort(key=lambda x: (x.get('score', 0), x.get('game_points', 0)), reverse=True)
            
            self.standings_table.setRowCount(len(teams))
            for row, team in enumerate(teams):
                item_rank = QTableWidgetItem(str(row + 1))
                item_rank.setTextAlignment(Qt.AlignCenter)
                self.standings_table.setItem(row, 0, item_rank)
                
                item_name = QTableWidgetItem(team['name'])
                item_name.setTextAlignment(Qt.AlignCenter)
                self.standings_table.setItem(row, 1, item_name)
                
                item_score = QTableWidgetItem(str(team.get('score', 0)))
                item_score.setTextAlignment(Qt.AlignCenter)
                self.standings_table.setItem(row, 2, item_score)
                
                item_game_points = QTableWidgetItem(str(team.get('game_points', 0)))
                item_game_points.setTextAlignment(Qt.AlignCenter)
                self.standings_table.setItem(row, 3, item_game_points)
        else:
            self.standings_table.setHorizontalHeaderLabels(["Rank", "Name", "Score", "SB"])
            standings = self.tie_break.calculate_tie_breaks(self.current_tournament['id'])
            self.standings_table.setRowCount(len(standings))
            for row, p in enumerate(standings):
                item_rank = QTableWidgetItem(str(row + 1))
                item_rank.setTextAlignment(Qt.AlignCenter)
                self.standings_table.setItem(row, 0, item_rank)
                
                item_name = QTableWidgetItem(p['name'])
                item_name.setTextAlignment(Qt.AlignCenter)
                self.standings_table.setItem(row, 1, item_name)
                
                item_score = QTableWidgetItem(str(p['score']))
                item_score.setTextAlignment(Qt.AlignCenter)
                self.standings_table.setItem(row, 2, item_score)
                
                item_sb = QTableWidgetItem(f"{p['sonneborn_berger']:.2f}")
                item_sb.setTextAlignment(Qt.AlignCenter)
                self.standings_table.setItem(row, 3, item_sb)

        # Update Action Bar Button
        rounds = self.round_manager.get_rounds(self.current_tournament['id'])
        if not rounds:
            self.generate_round_btn.setText("🚀 Start Tournament (Round 1)")
            self.generate_round_btn.setEnabled(True)
            self.round_status_label.setText("Tournament not started")
        else:
            last_round = rounds[-1]
            if self.round_manager.is_round_complete(last_round['id']):
                if len(rounds) < self.current_tournament['number_of_rounds']:
                    self.generate_round_btn.setText(f"Generate Round {len(rounds) + 1}")
                    self.generate_round_btn.setEnabled(True)
                    self.round_status_label.setText(f"Round {last_round['round_number']} Completed")
                else:
                    self.generate_round_btn.setText("Tournament Complete")
                    self.generate_round_btn.setEnabled(False)
                    self.round_status_label.setText("All rounds finished")
            else:
                self.generate_round_btn.setText("Current Round In Progress")
                self.generate_round_btn.setEnabled(False)
                self.round_status_label.setText(f"Round {last_round['round_number']} In Progress")

    def _load_rounds(self):
        self.round_combo.blockSignals(True)
        self.round_combo.clear()
        rounds = self.round_manager.get_rounds(self.current_tournament['id'])
        for r in rounds:
            self.round_combo.addItem(f"Round {r['round_number']}", r['id'])
        
        self.round_combo.blockSignals(False)
        
        # Select last round by default
        if rounds:
            self.round_combo.setCurrentIndex(len(rounds) - 1)
            self._load_selected_round(len(rounds) - 1)
        else:
            self.pairings_table.setRowCount(0)

    def _load_selected_round(self, index):
        if index < 0: return
        round_id = self.round_combo.itemData(index)
        self.current_round = round_id
        
        is_team = self.current_tournament.get("is_team_tournament", False)
        
        if is_team:
            self._load_team_round_results(round_id)
        else:
            self._load_player_round_results(round_id)

    def _load_team_round_results(self, round_id):
        results = self.round_manager.get_team_round_results(round_id)
        self.pairings_table.setRowCount(len(results))
        self.top_pairings_list.clear()
        
        from src.core.team_manager import TeamManager
        team_manager = TeamManager(self.tournament_manager.db)
        
        for row, res in enumerate(results):
            t1 = team_manager.get_team_by_id(res['team1_id'])
            t2 = team_manager.get_team_by_id(res['team2_id']) if res['team2_id'] else None
            
            t1_name = t1['name'] if t1 else "BYE"
            t2_name = t2['name'] if t2 else "BYE"
            
            # Populate Pairings Table
            item_board = QTableWidgetItem(str(row + 1))
            item_board.setTextAlignment(Qt.AlignCenter)
            self.pairings_table.setItem(row, 0, item_board)
            
            item_white = QTableWidgetItem(t1_name) # Assuming T1 is "Home/White"
            item_white.setTextAlignment(Qt.AlignCenter)
            self.pairings_table.setItem(row, 1, item_white)
            
            item_black = QTableWidgetItem(t2_name)
            item_black.setTextAlignment(Qt.AlignCenter)
            self.pairings_table.setItem(row, 2, item_black)
            
            result_str = self._get_result_text(res)
            item_result = QTableWidgetItem(result_str)
            item_result.setTextAlignment(Qt.AlignCenter)
            self.pairings_table.setItem(row, 3, item_result)
            
            # Action Button
            if not res['is_bye']:
                btn_text = "Edit Result" if res['winner_id'] is not None else "Enter Result"
                btn = QPushButton(btn_text)
                btn.setObjectName("tableActionButton")
                btn.clicked.connect(lambda checked, r=res: self._open_team_result_dialog(r))
                self.pairings_table.setCellWidget(row, 4, btn)
            else:
                 locked_label = QLabel("Locked")
                 locked_label.setAlignment(Qt.AlignCenter)
                 self.pairings_table.setCellWidget(row, 4, locked_label)

            # Populate Top Pairings List
            if row < 5:
                self.top_pairings_list.addItem(f"Match {row+1}: {t1_name} vs {t2_name} [{result_str}]")

    def _load_player_round_results(self, round_id):
        results = self.round_manager.get_round_results(round_id)
        self.pairings_table.setRowCount(len(results))
        self.top_pairings_list.clear()
        
        for row, res in enumerate(results):
            p1 = self.player_manager.get_player_by_id(res['player1_id'])
            p2 = self.player_manager.get_player_by_id(res['player2_id'])
            
            p1_name = p1['name'] if p1 else "BYE"
            p2_name = p2['name'] if p2 else "BYE"
            
            # Populate Pairings Table
            item_board = QTableWidgetItem(str(row + 1))
            item_board.setTextAlignment(Qt.AlignCenter)
            self.pairings_table.setItem(row, 0, item_board)
            
            item_white = QTableWidgetItem(p1_name)
            item_white.setTextAlignment(Qt.AlignCenter)
            self.pairings_table.setItem(row, 1, item_white)
            
            item_black = QTableWidgetItem(p2_name)
            item_black.setTextAlignment(Qt.AlignCenter)
            self.pairings_table.setItem(row, 2, item_black)
            
            result_str = self._get_result_text(res)
            item_result = QTableWidgetItem(result_str)
            item_result.setTextAlignment(Qt.AlignCenter)
            self.pairings_table.setItem(row, 3, item_result)
            
            # Action Button (Quick Result)
            if not res['is_bye']:
                btn_text = "Edit Result" if res['winner_id'] is not None else "Enter Result"
                btn = QPushButton(btn_text)
                btn.setObjectName("tableActionButton") # Added ID for styling
                btn.clicked.connect(lambda checked, r=res: self._open_result_dialog(r))
                self.pairings_table.setCellWidget(row, 4, btn)
            else:
                 locked_label = QLabel("Locked")
                 locked_label.setAlignment(Qt.AlignCenter)
                 self.pairings_table.setCellWidget(row, 4, locked_label)

            # Populate Top Pairings List (Top 5)
            if row < 5:
                self.top_pairings_list.addItem(f"Board {row+1}: {p1_name} vs {p2_name} [{result_str}]")

    def _open_team_result_dialog(self, result):
        """Open specialized board result dialog for team matches."""
        dialog = RoundManagementUI(self.round_manager, self.team_manager)
        dialog.set_tournament(self.current_tournament['id'])
        # Hack to trigger specific match dialog if we want to bypass the list
        from src.ui.board_result_entry import BoardResultDialog
        
        # Load match data to ensure it's up to date
        # result is a TeamResults dictionary. We need to find the corresponding TeamMatches record.
        # We match on tournament_id, round_number (via round_id), team1_id, and team2_id.
        
        # Get round number first
        round_info = next((r for r in self.round_manager.get_rounds(self.current_tournament['id']) if r['id'] == result['round_id']), None)
        if not round_info:
            return

        query = """
            SELECT * FROM TeamMatches 
            WHERE tournament_id = ? AND round_number = ? AND team1_id = ? AND (team2_id = ? OR (? IS NULL AND team2_id IS NULL))
        """
        params = (self.current_tournament['id'], round_info['round_number'], result['team1_id'], result['team2_id'], result['team2_id'])
        
        self.tournament_manager.db.cursor.execute(query, params)
        match_row = self.tournament_manager.db.cursor.fetchone()
        
        if not match_row:
            # Fallback or error if not found (should be created by create_round_with_pairings now)
            QMessageBox.warning(self, "Error", "Detailed match record not found.")
            return
        
        # Match dict from row
        match = {
            'id': match_row[0],
            'tournament_id': match_row[1],
            'round_number': match_row[2],
            'team1_id': match_row[3],
            'team2_id': match_row[4]
        }
        
        boards_per_match = self.current_tournament.get('boards_per_match', 4)
        
        board_dialog = BoardResultDialog(match, self.round_manager, self.team_manager, boards_per_match, self)
        if board_dialog.exec_() == QDialog.Accepted:
            self._load_selected_round(self.round_combo.currentIndex())
            self._refresh_dashboard_data()

    def _open_result_dialog(self, result):
        """Open a simple dialog to set the result."""
        p1 = self.player_manager.get_player_by_id(result['player1_id'])
        p2 = self.player_manager.get_player_by_id(result['player2_id'])
        p1_name = p1['name'] if p1 else "P1"
        p2_name = p2['name'] if p2 else "P2"
        
        items = [f"1-0 ({p1_name} wins)", f"0-1 ({p2_name} wins)", "½-½ (Draw)"]
        # Boards are usually shown as 1-indexed based on their position in the round
        board_number = self.pairings_table.currentRow() + 1
        if board_number <= 0: # row might be -1 if not selected, but we pass result dict anyway
            # Find the row by scanning for the result id in the table's user data or similar
            # For now, let's use the board number we assigned in _load_selected_round if possible
            # or just find which row matches this result id
            for row in range(self.pairings_table.rowCount()):
                 # Actually we don't store result in item data here, but we can find it
                 if self.pairings_table.item(row, 0).text() == str(result.get('board_number', row + 1)):
                      board_number = row + 1
                      break

        item, ok = QInputDialog.getItem(self, "Enter Result", 
                                        f"Result for Board {board_number}:", items, 0, False)
        
        if ok and item:
            winner_id = None
            if item.startswith("1-0"):
                winner_id = result['player1_id']
            elif item.startswith("0-1"):
                winner_id = result['player2_id']
            elif item.startswith("½-½"):
                winner_id = 0 # Draw
            
            self.round_manager.update_result(result['id'], winner_id)
            self._load_selected_round(self.round_combo.currentIndex()) # Refresh UI
            self._refresh_dashboard_data() # Refresh standings

    def _generate_next_round(self):
        if not self.current_tournament: return
        
        rounds = self.round_manager.get_rounds(self.current_tournament['id'])
        next_round_num = len(rounds) + 1
        
        # UI/UX: Show loading
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.generate_round_btn.setEnabled(False)
        self.generate_round_btn.setText("Generating...")
        QApplication.processEvents() # Force UI update

        try:
            self.round_manager.create_round_with_pairings(self.current_tournament['id'], next_round_num)
            QApplication.restoreOverrideCursor()
            QMessageBox.information(self, "Success", f"Round {next_round_num} generated!")
            self._load_rounds()
            self._refresh_dashboard_data()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", str(e))
            self._refresh_dashboard_data() # Reset button state

    def _load_players(self):
        if not self.current_tournament: return
        
        is_team = self.current_tournament.get("is_team_tournament", False)
        
        if is_team:
            from src.core.team_manager import TeamManager
            team_manager = TeamManager(self.tournament_manager.db)
            teams = team_manager.get_teams(self.current_tournament['id'])
            
            # Use same table structure but adapt headers if needed
            self.player_table.setColumnCount(5)
            self.player_table.setHorizontalHeaderLabels(["ID", "Team Name", "MP", "GP", "Rank"])
            
            # Sort teams for the player tab as well
            teams.sort(key=lambda x: (x.get('score', 0), x.get('game_points', 0)), reverse=True)
            
            self.player_table.setRowCount(len(teams))
            for row, team in enumerate(teams):
                item_id = QTableWidgetItem(str(team['id']))
                item_id.setTextAlignment(Qt.AlignCenter)
                self.player_table.setItem(row, 0, item_id)
                
                item_name = QTableWidgetItem(team['name'])
                item_name.setTextAlignment(Qt.AlignCenter)
                self.player_table.setItem(row, 1, item_name)
                
                item_score = QTableWidgetItem(str(team.get('score', 0)))
                item_score.setTextAlignment(Qt.AlignCenter)
                self.player_table.setItem(row, 2, item_score)

                item_gp = QTableWidgetItem(str(team.get('game_points', 0)))
                item_gp.setTextAlignment(Qt.AlignCenter)
                self.player_table.setItem(row, 3, item_gp)
                
                item_rank = QTableWidgetItem(str(row + 1)) # Rank based on sorted list
                item_rank.setTextAlignment(Qt.AlignCenter)
                self.player_table.setItem(row, 4, item_rank)
                
        else:
            self.player_table.setColumnCount(5)
            self.player_table.setHorizontalHeaderLabels(["ID", "Name", "Elo", "Fed", "Status"])
            
            players = self.player_manager.get_players(self.current_tournament['id'])
            self.player_table.setRowCount(len(players))
            for row, p in enumerate(players):
                item_id = QTableWidgetItem(str(p['id']))
                item_id.setTextAlignment(Qt.AlignCenter)
                self.player_table.setItem(row, 0, item_id)
                
                item_name = QTableWidgetItem(p['name'])
                item_name.setTextAlignment(Qt.AlignCenter)
                self.player_table.setItem(row, 1, item_name)
                
                item_elo = QTableWidgetItem(str(p['elo']))
                item_elo.setTextAlignment(Qt.AlignCenter)
                self.player_table.setItem(row, 2, item_elo)
                
                item_fed = QTableWidgetItem(p.get('federation', ''))
                item_fed.setTextAlignment(Qt.AlignCenter)
                self.player_table.setItem(row, 3, item_fed)
                
                status = "Withdrawn" if p.get('withdrawn') else "Active"
                item_status = QTableWidgetItem(status)
                item_status.setTextAlignment(Qt.AlignCenter)
                self.player_table.setItem(row, 4, item_status)

    def _add_new_player(self):
        if not self.current_tournament: return
        is_team = self.current_tournament.get("is_team_tournament", False)
        
        if is_team:
             name, ok = QInputDialog.getText(self, "Add Team", "Team Name:")
             if ok and name:
                 from src.core.team_manager import TeamManager
                 team_manager = TeamManager(self.tournament_manager.db)
                 team_manager.add_team(name, self.current_tournament['id'])
                 self._load_players()
                 self._refresh_dashboard_data()
        else:
            name, ok = QInputDialog.getText(self, "Add Player", "Name:")
            if ok and name:
                elo, ok2 = QInputDialog.getInt(self, "Add Player", "Elo:", 1000)
                if ok2:
                    self.player_manager.add_player(name, elo, self.current_tournament['id'])
                    self._load_players()
                    self._refresh_dashboard_data()

    def _withdraw_selected_player(self):
        sel = self.player_table.selectedItems()
        if not sel: return
        p_id = int(self.player_table.item(sel[0].row(), 0).text())
        if QMessageBox.question(self, "Confirm", "Withdraw player?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.player_manager.withdraw_player(p_id)
            self._load_players()

    def _export_standings(self, format_type: str):
        """Export standings to a file."""
        if not self.current_tournament:
            return

        standings = self.report_generator.generate_standings_report(self.current_tournament['id'])
        
        if format_type == "csv":
            filename, _ = QFileDialog.getSaveFileName(self, "Save Standings", f"standings_{self.current_tournament['name']}.csv", "CSV Files (*.csv)")
            if filename:
                fieldnames = ["rank", "name", "score", "buchholz", "sonneborn_berger", "performance"]
                self.report_generator.export_to_csv(standings, filename, fieldnames)
                QMessageBox.information(self, "Success", f"Standings exported to {filename}")
        
        elif format_type == "txt":
            filename, _ = QFileDialog.getSaveFileName(self, "Save Standings", f"standings_{self.current_tournament['name']}.txt", "Text Files (*.txt)")
            if filename:
                headers = {"rank": "Rank", "name": "Name", "score": "Score", "sonneborn_berger": "SB"}
                # Adjust format string based on headers
                format_str = "{rank:<5} {name:<25} {score:<10} {sonneborn_berger:<10}"
                
                self.report_generator.export_to_text(standings, filename, headers, format_str)
                QMessageBox.information(self, "Success", f"Standings exported to {filename}")

    def _export_pairings(self, format_type: str):
        """Export pairings to a file."""
        if not self.current_tournament:
            return
            
        round_index = self.round_combo.currentIndex()
        if round_index < 0:
            QMessageBox.warning(self, "Warning", "No round selected.")
            return

        # round_combo stores round_id as user data, but we need round number for report generation logic or just id
        # ReportGenerator.generate_pairings_report takes round_number.
        # Let's get the round object to find the number.
        round_id = self.round_combo.itemData(round_index)
        
        # We can extract round number from the combo text "Round X" or fetch it.
        # Fetching is safer.
        rounds = self.round_manager.get_rounds(self.current_tournament['id'])
        selected_round = next((r for r in rounds if r['id'] == round_id), None)
        
        if not selected_round:
            return

        pairings = self.report_generator.generate_pairings_report(self.current_tournament['id'], selected_round['round_number'])
        
        if format_type == "csv":
            filename, _ = QFileDialog.getSaveFileName(self, "Save Pairings", f"pairings_R{selected_round['round_number']}.csv", "CSV Files (*.csv)")
            if filename:
                fieldnames = ["table", "white", "black", "result"]
                self.report_generator.export_to_csv(pairings, filename, fieldnames)
                QMessageBox.information(self, "Success", f"Pairings exported to {filename}")
        
        elif format_type == "txt":
            filename, _ = QFileDialog.getSaveFileName(self, "Save Pairings", f"pairings_R{selected_round['round_number']}.txt", "Text Files (*.txt)")
            if filename:
                headers = {"table": "Bd", "white": "White", "black": "Black", "result": "Result"}
                format_str = "{table:<4} {white:<25} {black:<25} {result:<10}"
                self.report_generator.export_to_text(pairings, filename, headers, format_str)
                QMessageBox.information(self, "Success", f"Pairings exported to {filename}")


    def _get_result_text(self, result):
        if result['is_bye']: return "BYE"
        if result['winner_id'] is None: return "-"
        if result['winner_id'] == 0: return "½-½"
        
        # Determine if we are comparing player IDs or team IDs
        # Team results use 'team1_id', player results use 'player1_id'
        entity1_id = result.get('player1_id')
        if entity1_id is None:
             entity1_id = result.get('team1_id')
             
        if result['winner_id'] == entity1_id: return "1-0"
        return "0-1"

    def show(self):
        """Override show to refresh list."""
        super().show()
        self._refresh_tournament_list()
