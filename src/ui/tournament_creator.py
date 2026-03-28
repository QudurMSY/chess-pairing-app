"""
Tournament Creator UI module for the Chess Pairing App.
This module defines the UI for creating new tournaments with player registration and format selection,
implementing a split-screen layout with live summary.
"""

import logging
import math
import os
import pandas as pd
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QListWidget, QComboBox, QMessageBox,
                             QFileDialog, QTabWidget, QFormLayout, QSpinBox,
                             QCheckBox, QTextEdit, QGridLayout, QFrame, QScrollArea,
                             QToolBox, QGroupBox)
from PyQt5.QtCore import Qt
from src.core.tournament_manager import TournamentManager
from src.core.player_manager import PlayerManager
from src.core.round_manager import RoundManager

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TournamentCreatorUI(QWidget):
    """UI for creating new tournaments with split-screen layout."""

    def __init__(self, tournament_manager: TournamentManager, 
                 player_manager: PlayerManager, round_manager: RoundManager):
        super().__init__()
        logger.info("TournamentCreatorUI __init__ called")
        
        self.tournament_manager = tournament_manager
        self.player_manager = player_manager
        self.round_manager = round_manager
        self.current_tournament_id = None
        self.players = []
        self.teams = []
        
        self.init_ui()
        logger.info("TournamentCreatorUI initialization completed")

    def init_ui(self):
        """Initialize the UI components."""
        logger.info("TournamentCreatorUI init_ui called")
        
        # Main layout is Horizontal (Split Screen)
        main_layout = QHBoxLayout()
        
        # --- Left Side: Input Forms (Accordion/ToolBox) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.tool_box = QToolBox()
        
        # Section 1: Tournament Info
        self.tournament_info_widget = self._create_tournament_info_widget()
        self.tool_box.addItem(self.tournament_info_widget, "1. Tournament Info")
        
        # Section 2: Player Registration
        self.player_registration_widget = self._create_player_registration_widget()
        self.tool_box.addItem(self.player_registration_widget, "2. Player Registration")
        
        # Section 3: Team Player Registration (Initially hidden/removed or handled dynamically)
        self.team_player_registration_widget = self._create_team_player_registration_widget()
        # We don't add it yet, we'll add/remove based on mode
        
        # Section 3 (or 4): Format Selection
        self.format_selection_widget = self._create_format_selection_widget()
        self.tool_box.addItem(self.format_selection_widget, "3. Format Selection")
        
        left_layout.addWidget(self.tool_box)
        
        # Action Buttons Area (at bottom of left side)
        action_layout = QHBoxLayout()
        self.create_button = QPushButton("🎉 Create Tournament")
        self.create_button.setFixedSize(200, 50)
        self.create_button.setToolTip("Finalize and create the tournament with the current settings")
        self.create_button.clicked.connect(self._create_tournament)
        self.create_button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; border: none;")
        action_layout.addWidget(self.create_button)
        
        left_layout.addLayout(action_layout)
        
        # --- Right Side: Live Summary ---
        right_widget = QWidget()
        right_widget.setFixedWidth(350)
        right_widget.setStyleSheet("background-color: #ffffff; border-left: 1px solid #e0e0e0;")
        right_layout = QVBoxLayout(right_widget)
        
        summary_title = QLabel("Tournament Summary")
        summary_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        right_layout.addWidget(summary_title)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("border: none; background-color: transparent;")
        right_layout.addWidget(self.summary_text)
        
        # Add widgets to main layout
        main_layout.addWidget(left_widget, 2) # Left side takes 2/3 space
        main_layout.addWidget(right_widget, 1) # Right side takes 1/3 space
        
        self.setLayout(main_layout)
        
        # Initial Summary Update
        self._update_summary()
        logger.info("TournamentCreatorUI layout set")

    def _create_tournament_info_widget(self):
        """Create the tournament info widget."""
        widget = QWidget()
        form_layout = QFormLayout(widget)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setContentsMargins(10, 10, 10, 10)

        # Tournament name
        self.tournament_name_input = QLineEdit()
        self.tournament_name_input.setPlaceholderText("e.g., Spring Open 2024")
        self.tournament_name_input.setToolTip("Enter the official name of the tournament")
        self.tournament_name_input.textChanged.connect(self._update_summary)
        form_layout.addRow("Tournament Name:", self.tournament_name_input)

        # Team Tournament Checkbox
        self.is_team_tournament_checkbox = QCheckBox("Team Tournament")
        self.is_team_tournament_checkbox.setToolTip("Check if this is a team-based tournament")
        self.is_team_tournament_checkbox.stateChanged.connect(self._toggle_team_mode)
        self.is_team_tournament_checkbox.stateChanged.connect(self._update_summary)
        form_layout.addRow("", self.is_team_tournament_checkbox)

        # Boards per match (for team tournaments)
        self.boards_per_match_spin = QSpinBox()
        self.boards_per_match_spin.setRange(1, 100)
        self.boards_per_match_spin.setValue(4)
        self.boards_per_match_spin.setToolTip("Number of boards per match in a team tournament")
        self.boards_per_match_spin.setVisible(False)
        self.boards_per_match_spin.valueChanged.connect(self._update_summary)
        self.boards_per_match_label = QLabel("Boards per Match:")
        self.boards_per_match_label.setVisible(False)
        form_layout.addRow(self.boards_per_match_label, self.boards_per_match_spin)

        # Start date
        self.start_date_input = QLineEdit()
        self.start_date_input.setPlaceholderText("YYYY-MM-DD")
        self.start_date_input.setToolTip("Start date in YYYY-MM-DD format")
        self.start_date_input.textChanged.connect(self._update_summary)
        form_layout.addRow("Start Date:", self.start_date_input)

        # Location
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("City, Country")
        self.location_input.setToolTip("Location where the tournament is held")
        self.location_input.textChanged.connect(self._update_summary)
        form_layout.addRow("Location:", self.location_input)

        # Organizer
        self.organizer_input = QLineEdit()
        self.organizer_input.setPlaceholderText("Organizer Name")
        self.organizer_input.setToolTip("Name of the organizer or arbiter")
        self.organizer_input.textChanged.connect(self._update_summary)
        form_layout.addRow("Organizer:", self.organizer_input)

        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Tournament description...")
        self.description_input.setToolTip("Additional details or rules for the tournament")
        self.description_input.setFixedHeight(80)
        form_layout.addRow("Description:", self.description_input)

        return widget

    def _toggle_team_mode(self):
        """Toggle between Player and Team registration modes."""
        is_team = self.is_team_tournament_checkbox.isChecked()
        
        # Update toolbox title for the second section
        self.tool_box.setItemText(1, "2. Team Registration" if is_team else "2. Player Registration")
        
        # Toggle visibility of registration groups within the second section
        self.manual_player_group.setVisible(not is_team)
        self.manual_team_group.setVisible(is_team)
        
        # Toggle visibility of boards_per_match in the first section
        self.boards_per_match_spin.setVisible(is_team)
        self.boards_per_match_label.setVisible(is_team)
        
        # Update list label in the second section
        self.list_label.setText("Registered Teams:" if is_team else "Registered Players:")
        
        # Manage the "Team Player Registration" section in the toolbox
        # Current indices: 0=Info, 1=Registration, 2=Format (Individual) OR 2=TeamPlayer, 3=Format (Team)
        
        if is_team:
            # We are in Team mode. Check if the Team Player Registration section is already there.
            # If the third item (index 2) is the format selection widget, we need to insert the team player widget.
            if self.tool_box.widget(2) == self.format_selection_widget:
                # Insert Team Player Registration at index 2
                self.tool_box.insertItem(2, self.team_player_registration_widget, "3. Player Registration")
                # Update Format Selection title
                self.tool_box.setItemText(3, "4. Format Selection")
        else:
            # We are in Individual mode. Check if Team Player Registration section is present.
            # If the third item (index 2) is the team player widget, remove it.
            if self.tool_box.widget(2) == self.team_player_registration_widget:
                self.tool_box.removeItem(2)
                # Update Format Selection title
                self.tool_box.setItemText(2, "3. Format Selection")
        
        # Clear lists to avoid confusion
        self.players = []
        self.teams = [] 
        self._update_player_list()
        self._update_team_player_list_combo() # Refresh the team combo in the new section

    def _create_player_registration_widget(self):
        """Create the player/team registration widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # --- Manual Player Entry Group ---
        self.manual_player_group = QGroupBox("Add Player Manually")
        manual_form = QFormLayout(self.manual_player_group)

        self.player_name_input = QLineEdit()
        self.player_name_input.setPlaceholderText("Full Name")
        self.player_name_input.setToolTip("Player's first name")
        manual_form.addRow("Name:", self.player_name_input)

        self.player_surname_input = QLineEdit()
        self.player_surname_input.setPlaceholderText("Surname")
        self.player_surname_input.setToolTip("Player's last name")
        manual_form.addRow("Surname:", self.player_surname_input)

        self.player_elo_input = QLineEdit()
        self.player_elo_input.setPlaceholderText("Elo Rating")
        self.player_elo_input.setToolTip("Player's Elo rating (default: 0)")
        manual_form.addRow("Elo:", self.player_elo_input)
        
        # FIDE ID & Federation in one row to save space
        fide_row = QHBoxLayout()
        self.player_fide_id_input = QLineEdit()
        self.player_fide_id_input.setPlaceholderText("FIDE ID")
        self.player_fide_id_input.setToolTip("Player's FIDE ID (optional)")
        fide_row.addWidget(self.player_fide_id_input)
        
        self.player_federation_input = QLineEdit()
        self.player_federation_input.setPlaceholderText("Fed")
        self.player_federation_input.setToolTip("Three-letter Federation code (e.g., USA, IND)")
        self.player_federation_input.setFixedWidth(60)
        fide_row.addWidget(self.player_federation_input)
        manual_form.addRow("FIDE / Fed:", fide_row)

        add_player_button = QPushButton("➕ Add Player")
        add_player_button.setToolTip("Add this player to the list")
        add_player_button.clicked.connect(self._add_player_manually)
        manual_form.addRow(add_player_button)
        
        layout.addWidget(self.manual_player_group)

        # --- Manual Team Entry Group (Hidden by default) ---
        self.manual_team_group = QGroupBox("Add Team Manually")
        self.manual_team_group.setVisible(False)
        team_form = QFormLayout(self.manual_team_group)

        self.team_name_input = QLineEdit()
        self.team_name_input.setPlaceholderText("Team Name")
        team_form.addRow("Team Name:", self.team_name_input)

        add_team_button = QPushButton("➕ Add Team")
        add_team_button.clicked.connect(self._add_team_manually)
        team_form.addRow(add_team_button)

        layout.addWidget(self.manual_team_group)

        # Import button
        import_button = QPushButton("📁 Import Players from TXT")
        import_button.setToolTip("Import players from a text file (Name, Elo, FIDE ID, Fed)")
        import_button.clicked.connect(self._import_players_from_file)
        layout.addWidget(import_button)

        # Player/Team list
        self.list_label = QLabel("Registered Players:")
        layout.addWidget(self.list_label)

        self.player_list = QListWidget()
        self.player_list.setFixedHeight(150)
        self.player_list.setToolTip("List of currently registered players/teams")
        layout.addWidget(self.player_list)

        # Actions
        actions_layout = QHBoxLayout()
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setToolTip("Remove the selected player/team from the list")
        remove_btn.clicked.connect(self._remove_selected_player)
        actions_layout.addWidget(remove_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.setToolTip("Remove all players/teams from the list")
        clear_btn.clicked.connect(self._clear_all_players)
        actions_layout.addWidget(clear_btn)
        
        layout.addLayout(actions_layout)

        return widget

    def _create_team_player_registration_widget(self):
        """Create the widget for registering players to teams."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Team Selection
        team_select_layout = QHBoxLayout()
        team_select_layout.addWidget(QLabel("Select Team:"))
        self.team_selection_combo = QComboBox()
        self.team_selection_combo.setToolTip("Select a team to add players to")
        self.team_selection_combo.currentIndexChanged.connect(self._update_team_players_list)
        team_select_layout.addWidget(self.team_selection_combo)
        layout.addLayout(team_select_layout)

        # Player Entry Form
        form_group = QGroupBox("Add Player to Team")
        form_layout = QFormLayout(form_group)

        self.team_player_name_input = QLineEdit()
        self.team_player_name_input.setPlaceholderText("Full Name")
        form_layout.addRow("Name:", self.team_player_name_input)
        
        self.team_player_elo_input = QLineEdit()
        self.team_player_elo_input.setPlaceholderText("Elo Rating")
        form_layout.addRow("Elo:", self.team_player_elo_input)

        self.team_player_board_spin = QSpinBox()
        self.team_player_board_spin.setRange(1, 100)
        self.team_player_board_spin.setValue(1)
        self.team_player_board_spin.setEnabled(False) # Auto-assigned
        self.team_player_board_spin.setToolTip("Board order is automatically assigned")
        form_layout.addRow("Board Order:", self.team_player_board_spin)

        add_btn = QPushButton("➕ Add Player to Team")
        add_btn.clicked.connect(self._add_team_player)
        form_layout.addRow(add_btn)
        
        layout.addWidget(form_group)

        # Team Players List
        layout.addWidget(QLabel("Team Roster:"))
        self.team_players_list_widget = QListWidget()
        self.team_players_list_widget.setFixedHeight(150)
        layout.addWidget(self.team_players_list_widget)

        # Actions
        actions_layout = QHBoxLayout()
        remove_btn = QPushButton("Remove Selected Player")
        remove_btn.clicked.connect(self._remove_selected_team_player)
        actions_layout.addWidget(remove_btn)
        layout.addLayout(actions_layout)

        return widget

    def _update_team_player_list_combo(self):
        """Update the team selection combobox."""
        current_team_idx = self.team_selection_combo.currentIndex()
        self.team_selection_combo.blockSignals(True)
        self.team_selection_combo.clear()
        
        for team in self.teams:
            self.team_selection_combo.addItem(team['name'])
            
        if 0 <= current_team_idx < len(self.teams):
            self.team_selection_combo.setCurrentIndex(current_team_idx)
        elif self.teams:
            self.team_selection_combo.setCurrentIndex(0)
            
        self.team_selection_combo.blockSignals(False)
        self._update_team_players_list()

    def _update_team_players_list(self):
        """Update the list of players for the selected team."""
        self.team_players_list_widget.clear()
        idx = self.team_selection_combo.currentIndex()
        if idx < 0 or idx >= len(self.teams):
            self.team_player_board_spin.setValue(1)
            return

        team = self.teams[idx]
        players = team.get('players', [])
        # Sort by board order
        players.sort(key=lambda x: x.get('board_order', 999))
        
        for p in players:
            text = f"Board {p.get('board_order', '?')}: {p['name']} ({p.get('elo', 0)})"
            self.team_players_list_widget.addItem(text)
            
        # Update spinbox to the next available board number
        next_board = len(players) + 1
        self.team_player_board_spin.setValue(next_board)

    def _add_team_player(self):
        """Add a player to the currently selected team."""
        idx = self.team_selection_combo.currentIndex()
        if idx < 0 or idx >= len(self.teams):
            QMessageBox.warning(self, "Error", "No team selected. Please create a team first.")
            return

        name = self.team_player_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Player name is required.")
            return

        try:
            elo = int(self.team_player_elo_input.text().strip()) if self.team_player_elo_input.text().strip() else 0
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid Elo.")
            return

        player_info = {
            'name': name,
            'elo': elo,
            'board_order': self.team_player_board_spin.value()
        }

        # Initialize players list if not present
        if 'players' not in self.teams[idx]:
            self.teams[idx]['players'] = []
            
        self.teams[idx]['players'].append(player_info)
        
        # Clear inputs
        self.team_player_name_input.clear()
        self.team_player_elo_input.clear()
        self.team_player_name_input.setFocus()
        
        self._update_team_players_list()
        self._update_summary()

    def _remove_selected_team_player(self):
        """Remove the selected player from the team."""
        team_idx = self.team_selection_combo.currentIndex()
        if team_idx < 0 or team_idx >= len(self.teams):
            return
            
        row = self.team_players_list_widget.currentRow()
        if row < 0:
            return
            
        team = self.teams[team_idx]
        if 'players' in team and 0 <= row < len(team['players']):
            team['players'].pop(row)
            
            # Reassign board orders to maintain sequential order
            for i, p in enumerate(team['players']):
                p['board_order'] = i + 1
                
            self._update_team_players_list()
            self._update_summary()

    def _create_format_selection_widget(self):
        """Create the format selection widget."""
        widget = QWidget()
        form_layout = QFormLayout(widget)
        form_layout.setContentsMargins(10, 10, 10, 10)

        # Pairing system
        self.pairing_system_combo = QComboBox()
        self.pairing_system_combo.addItems([
            "Dutch System", "Swiss System", "Dubov System", "Berger Table",
            "Burstein System", "Lim System", "Double Swiss System"
        ])
        self.pairing_system_combo.setToolTip("Select the pairing system for the tournament")
        self.pairing_system_combo.currentTextChanged.connect(self._update_summary)
        form_layout.addRow("Pairing System:", self.pairing_system_combo)

        # Round calculation
        round_layout = QHBoxLayout()
        self.auto_rounds_checkbox = QCheckBox("Auto")
        self.auto_rounds_checkbox.setChecked(True)
        self.auto_rounds_checkbox.setToolTip("Automatically calculate rounds based on player count")
        self.auto_rounds_checkbox.stateChanged.connect(self._update_round_count)
        round_layout.addWidget(self.auto_rounds_checkbox)

        self.round_count_spin = QSpinBox()
        self.round_count_spin.setRange(1, 20)
        self.round_count_spin.setEnabled(False)
        self.round_count_spin.setValue(5)
        self.round_count_spin.setToolTip("Number of rounds (disable Auto to edit manually)")
        self.round_count_spin.valueChanged.connect(self._update_summary)
        round_layout.addWidget(self.round_count_spin)
        form_layout.addRow("Rounds:", round_layout)

        # Time control
        self.time_control_combo = QComboBox()
        self.time_control_combo.addItems(["Standard (90+30)", "Rapid (15+10)", "Blitz (3+2)", "Bullet (1+1)", "Custom"])
        self.time_control_combo.setToolTip("Select the time control for the games")
        self.time_control_combo.currentIndexChanged.connect(self._update_custom_time_control_visibility)
        self.time_control_combo.currentTextChanged.connect(self._update_summary)
        form_layout.addRow("Time Control:", self.time_control_combo)

        # Custom time control
        self.custom_time_input = QLineEdit()
        self.custom_time_input.setPlaceholderText("e.g., 60+30")
        self.custom_time_input.setToolTip("Enter custom time control (e.g., '60+30')")
        self.custom_time_input.setVisible(False)
        form_layout.addRow("Custom Time:", self.custom_time_input)

        # Tie-break system
        self.tie_break_combo = QComboBox()
        self.tie_break_combo.addItems(["Sonnenborn-Berger", "Buchholz", "Progressive Score", "Direct Encounter"])
        self.tie_break_combo.setToolTip("Primary tie-break system for standings")
        self.tie_break_combo.currentTextChanged.connect(self._update_summary)
        form_layout.addRow("Tie-Break:", self.tie_break_combo)

        # Advanced options group
        adv_group = QGroupBox("Advanced Options")
        adv_layout = QVBoxLayout(adv_group)
        
        self.allow_byes_checkbox = QCheckBox("Allow byes")
        self.allow_byes_checkbox.setChecked(True)
        self.allow_byes_checkbox.setToolTip("Allow players to receive a bye if there is an odd number of players")
        self.allow_byes_checkbox.stateChanged.connect(self._update_summary)
        adv_layout.addWidget(self.allow_byes_checkbox)

        self.accelerated_pairing_checkbox = QCheckBox("Accelerated Pairing")
        self.accelerated_pairing_checkbox.setToolTip("Use accelerated pairings for the first rounds")
        self.accelerated_pairing_checkbox.stateChanged.connect(self._update_summary)
        adv_layout.addWidget(self.accelerated_pairing_checkbox)

        self.fide_rules_checkbox = QCheckBox("FIDE Compliant")
        self.fide_rules_checkbox.setChecked(True)
        self.fide_rules_checkbox.setToolTip("Enforce strict FIDE rules for pairings and ratings")
        self.fide_rules_checkbox.stateChanged.connect(self._update_summary)
        adv_layout.addWidget(self.fide_rules_checkbox)
        
        form_layout.addRow(adv_group)

        return widget

    def _update_custom_time_control_visibility(self):
        """Shows or hides the custom time control input."""
        is_custom = self.time_control_combo.currentText() == "Custom"
        self.custom_time_input.setVisible(is_custom)

    def _update_summary(self):
        """Update the live summary text."""
        name = self.tournament_name_input.text() or "[Tournament Name]"
        date = self.start_date_input.text() or "[Date]"
        location = self.location_input.text()
        organizer = self.organizer_input.text()
        
        pairing = self.pairing_system_combo.currentText()
        rounds = self.round_count_spin.value()
        time_control = self.time_control_combo.currentText()
        tie_break = self.tie_break_combo.currentText()
        
        is_team = self.is_team_tournament_checkbox.isChecked()
        count = len(self.teams) if is_team else len(self.players)
        type_str = "Teams" if is_team else "Players"
        
        summary_html = f"""
        <h3 style="color: #007bff;">{name}</h3>
        <p><b>Type:</b> {'Team Tournament' if is_team else 'Individual Tournament'}</p>
        """
        if is_team:
            summary_html += f"<p><b>Boards per Match:</b> {self.boards_per_match_spin.value()}</p>"
            
        summary_html += f"<p><b>Date:</b> {date}</p>"
        
        if location:
            summary_html += f"<p><b>Location:</b> {location}</p>"
        if organizer:
            summary_html += f"<p><b>Organizer:</b> {organizer}</p>"
            
        summary_html += f"""
        <hr>
        <p><b>{type_str}:</b> {count}</p>
        <p><b>Format:</b></p>
        <ul>
            <li>{pairing}</li>
            <li>{rounds} Rounds</li>
            <li>{time_control}</li>
            <li>{tie_break}</li>
        </ul>
        <hr>
        <p><b>Settings:</b></p>
        <ul>
            <li>Byes: {'Yes' if self.allow_byes_checkbox.isChecked() else 'No'}</li>
            <li>Accelerated: {'Yes' if self.accelerated_pairing_checkbox.isChecked() else 'No'}</li>
            <li>FIDE Strict: {'Yes' if self.fide_rules_checkbox.isChecked() else 'No'}</li>
        </ul>
        """
        
        self.summary_text.setHtml(summary_html)

    def _add_player_manually(self):
        """Add a player manually."""
        name = self.player_name_input.text().strip()
        surname = self.player_surname_input.text().strip()
        elo_text = self.player_elo_input.text().strip()
        fide_id = self.player_fide_id_input.text().strip()
        federation = self.player_federation_input.text().strip()
        
        if not name or not surname:
            QMessageBox.warning(self, "Validation Error", "Name and surname are required.")
            return
        
        try:
            elo = int(elo_text) if elo_text else 0
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Elo must be a valid number.")
            return
        
        player_info = {
            'name': f"{name} {surname}",
            'elo': elo,
            'fide_id': fide_id,
            'federation': federation
        }
        
        self.players.append(player_info)
        self._update_player_list()
        
        # Clear inputs
        self.player_name_input.clear()
        self.player_surname_input.clear()
        self.player_elo_input.clear()
        self.player_fide_id_input.clear()
        self.player_federation_input.clear()
        self.player_name_input.setFocus()

    def _add_team_manually(self):
        """Add a team manually."""
        name = self.team_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Team name is required.")
            return

        team_info = {
            'name': name
        }
        
        self.teams.append(team_info)
        self._update_player_list()
        
        # Clear inputs
        self.team_name_input.clear()
        self.team_name_input.setFocus()

    def _remove_selected_player(self):
        """Remove the selected player or team."""
        selected_items = self.player_list.selectedItems()
        if not selected_items:
            return
        
        row = self.player_list.row(selected_items[0])
        
        if self.is_team_tournament_checkbox.isChecked():
            if 0 <= row < len(self.teams):
                self.teams.pop(row)
                self._update_player_list()
        else:
            if 0 <= row < len(self.players):
                self.players.pop(row)
                self._update_player_list()

    def _clear_all_players(self):
        """Clear all players or teams."""
        is_team = self.is_team_tournament_checkbox.isChecked()
        items = self.teams if is_team else self.players
        
        if items:
            confirm = QMessageBox.question(
                self, "Confirm Clear", 
                f"Remove all {'teams' if is_team else 'players'}?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                if is_team:
                    self.teams = []
                else:
                    self.players = []
                self._update_player_list()

        
    def _import_players_from_file(self):
        """Import players from a text file into the temporary list."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Player File", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            result = self.player_manager.import_players_from_file(file_path)
            
            if result['success']:
                new_players = result['players']
                count = 0
                for p in new_players:
                    player_info = {
                        'name': p['name'],
                        'elo': p.get('elo', 0),
                        'fide_id': p.get('fide_id'),
                        'federation': p.get('federation')
                    }
                    self.players.append(player_info)
                    count += 1
                
                self._update_player_list()
                
                msg = f"Successfully imported {count} players."
                if result['errors']:
                    msg += f"\n\n{len(result['errors'])} lines skipped/errors."
                QMessageBox.information(self, "Import Success", msg)
            else:
                QMessageBox.warning(self, "Import Failed", 
                                    f"Failed to import players.\nErrors:\n{', '.join(result['errors'][:5])}")
                
        except Exception as e:
            logger.exception("Error importing players in TournamentCreator")
            QMessageBox.critical(self, "Error", f"An error occurred during import: {str(e)}")

    def _update_player_list(self):
        """Update the player/team list display."""
        self.player_list.clear()
        
        is_team = self.is_team_tournament_checkbox.isChecked()
        
        if is_team:
            for i, team in enumerate(self.teams, 1):
                text = f"{i}. {team['name']}"
                self.player_list.addItem(text)
            self._update_team_player_list_combo()
        else:
            for i, player in enumerate(self.players, 1):
                text = f"{i}. {player['name']} ({player['elo']})"
                if player.get('federation'):
                    text += f" [{player['federation']}]"
                self.player_list.addItem(text)
        
        self._update_round_count()
        self._update_summary()

    def _update_round_count(self):
        """Update the round count based on player/team count."""
        if self.auto_rounds_checkbox.isChecked():
            count = len(self.teams) if self.is_team_tournament_checkbox.isChecked() else len(self.players)
            if count >= 2:
                rounds = math.ceil(math.sqrt(count))
                self.round_count_spin.setValue(max(1, min(rounds, 20)))
                self.round_count_spin.setEnabled(False)
            else:
                self.round_count_spin.setValue(1)
        else:
            self.round_count_spin.setEnabled(True)
        self._update_summary()

    def _create_tournament(self):
        """Create the tournament."""
        # Validation
        if not self.tournament_name_input.text().strip():
            QMessageBox.warning(self, "Error", "Tournament name required.")
            self.tool_box.setCurrentIndex(0)
            return
        if not self.start_date_input.text().strip():
            QMessageBox.warning(self, "Error", "Start date required.")
            self.tool_box.setCurrentIndex(0)
            return
            
        is_team = self.is_team_tournament_checkbox.isChecked()
        count = len(self.teams) if is_team else len(self.players)
        
        if count < 2:
            QMessageBox.warning(self, "Error", f"At least 2 {'teams' if is_team else 'players'} required.")
            self.tool_box.setCurrentIndex(1)
            return

        try:
            tournament_id = self.tournament_manager.create_tournament(
                name=self.tournament_name_input.text(),
                start_date=self.start_date_input.text(),
                number_of_rounds=self.round_count_spin.value(),
                pairing_system=self.pairing_system_combo.currentText(),
                is_team_tournament=is_team,
                boards_per_match=self.boards_per_match_spin.value() if is_team else None
            )
            
            from src.core.team_manager import TeamManager
            team_manager = TeamManager(self.tournament_manager.db)

            if is_team:
                for team in self.teams:
                    team_id = team_manager.add_team(team['name'], tournament_id)
                    
                    # Add players to the team if any
                    if 'players' in team:
                        for p in team['players']:
                            # First add player to the global Players table for this tournament
                            player_id = self.player_manager.add_player(
                                name=p['name'],
                                elo=p['elo'],
                                tournament_id=tournament_id,
                                fide_id=p.get('fide_id'),
                                federation=p.get('federation', 'UNK')
                            )
                            # Then link to the team
                            team_manager.add_player_to_team(
                                team_id=team_id,
                                player_id=player_id,
                                board_order=p.get('board_order', 1)
                            )
            else:
                for player in self.players:
                    self.player_manager.add_player(
                        name=player['name'],
                        elo=player['elo'],
                        tournament_id=tournament_id,
                        fide_id=player.get('fide_id'),
                        federation=player.get('federation', 'UNK')
                    )
            
            # Create first round
            self.round_manager.create_round_with_pairings(tournament_id, 1)
            
            QMessageBox.information(self, "Success", "Tournament Created!")
            
            # Reset form
            self.players = []
            self.teams = []
            self.tournament_name_input.clear()
            self._update_player_list()
            self.tool_box.setCurrentIndex(0)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Creation failed: {str(e)}")

