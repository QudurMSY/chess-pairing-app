"""
Tournament management UI module for the Chess Pairing App.
This module defines the UI for tournament creation and management.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QComboBox, QMessageBox
)
from src.core.tournament_manager import TournamentManager

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TournamentManagementUI(QWidget):
    """UI for tournament creation and management."""

    def __init__(self, tournament_manager: TournamentManager):
        super().__init__()
        logger.info("TournamentManagementUI __init__ called")
        logger.debug(f"Tournament manager instance: {tournament_manager}")
        self.tournament_manager = tournament_manager
        self.init_ui()
        logger.info("TournamentManagementUI initialization completed")

    def init_ui(self):
        """Initialize the UI components."""
        logger.info("TournamentManagementUI init_ui called")
        layout = QVBoxLayout()
        
        # Tournament creation form
        form_layout = QHBoxLayout()
        
        name_label = QLabel("Name:")
        self.name_input = QLineEdit()
        
        start_date_label = QLabel("Start Date:")
        self.start_date_input = QLineEdit()
        
        rounds_label = QLabel("Number of Rounds:")
        self.rounds_input = QLineEdit()
        
        pairing_system_label = QLabel("Pairing System:")
        self.pairing_system_input = QComboBox()
        self.pairing_system_input.addItems([
            "Swiss", "Berger Table", "Burstein", "Dubov", "Lim", "Double Swiss"
        ])
        
        is_team_label = QLabel("Is Team Tournament:")
        self.is_team_input = QComboBox()
        self.is_team_input.addItems(["False", "True"])
        
        create_button = QPushButton("Create Tournament")
        create_button.clicked.connect(self.create_tournament)
        
        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(start_date_label)
        form_layout.addWidget(self.start_date_input)
        form_layout.addWidget(rounds_label)
        form_layout.addWidget(self.rounds_input)
        form_layout.addWidget(pairing_system_label)
        form_layout.addWidget(self.pairing_system_input)
        form_layout.addWidget(is_team_label)
        form_layout.addWidget(self.is_team_input)
        form_layout.addWidget(create_button)
        
        layout.addLayout(form_layout)
        
        # Tournament list
        self.tournament_list = QListWidget()
        layout.addWidget(self.tournament_list)
        
        # Refresh button
        refresh_button = QPushButton("Refresh Tournament List")
        refresh_button.clicked.connect(self.refresh_tournament_list)
        layout.addWidget(refresh_button)
        
        self.setLayout(layout)
        logger.info("TournamentManagementUI layout set")
        
        # Set window properties
        self.setWindowTitle("Tournament Management")
        self.resize(800, 600)
        logger.info("TournamentManagementUI window properties set")

    def create_tournament(self):
        """Create a new tournament."""
        name = self.name_input.text()
        start_date = self.start_date_input.text()
        number_of_rounds = int(self.rounds_input.text())
        pairing_system = self.pairing_system_input.currentText()
        is_team_tournament = self.is_team_input.currentText() == "True"
        
        tournament_id = self.tournament_manager.create_tournament(
            name, start_date, number_of_rounds, pairing_system, is_team_tournament
        )
        
        QMessageBox.information(self, "Success", f"Tournament created with ID: {tournament_id}")
        
        self.refresh_tournament_list()

    def refresh_tournament_list(self):
        """Refresh the tournament list."""
        self.tournament_list.clear()
        
        tournaments = self.tournament_manager.get_tournaments()
        
        for tournament in tournaments:
            self.tournament_list.addItem(
                f"{tournament['name']} (Rounds: {tournament['number_of_rounds']}, "
                f"System: {tournament['pairing_system']})"
            )