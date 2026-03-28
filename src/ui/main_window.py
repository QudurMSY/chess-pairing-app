"""
Main window for the Chess Pairing App.
This module defines the main application window and its layout, implementing a sidebar navigation system.
"""

import logging
import os
import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QGridLayout, QLabel, QPushButton, 
                             QMessageBox, QHBoxLayout, QVBoxLayout, QStackedWidget, QFrame)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from src.ui.tournament_creator import TournamentCreatorUI
from src.ui.tournament_manager_ui import TournamentManagerUI
from src.core.player_manager import PlayerManager
from src.core.tournament_manager import TournamentManager
from src.core.round_manager import RoundManager
from src.core.team_manager import TeamManager
from src.database.database import Database
from src.memory.memory_bank import MemoryBank

# Configure logging for the application
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for the Chess Pairing App."""

    def __init__(self):
        super().__init__()
        logger.info("Initializing MainWindow")

        self.setWindowTitle("Chess Tournament Manager")
        self.resize(1200, 800)  # Larger default size for sidebar layout

        # Load and apply stylesheet
        self._load_stylesheet()

        # Initialize database, managers, and memory bank
        self.db = Database()
        self.player_manager = PlayerManager(self.db)
        self.tournament_manager = TournamentManager(self.db)
        self.team_manager = TeamManager(self.db)
        self.round_manager = RoundManager(self.db, self.tournament_manager)
        self.memory_bank = MemoryBank()

        # Flag for test mode
        self.test_mode = os.environ.get("APP_TEST_MODE", "false").lower() == "true"

        # Ensure the save directory for tournaments exists
        self._create_save_directory()

        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(250)
        self.sidebar.setMaximumWidth(300)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(10)

        # App Title in Sidebar
        app_title = QLabel("Chess Manager")
        app_title.setObjectName("sidebarTitle")
        app_title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(app_title)

        # Navigation Buttons
        self.nav_buttons = {}
        
        self._add_sidebar_button(sidebar_layout, "home", "🏠 Home", self._show_home)
        self._add_sidebar_button(sidebar_layout, "create", "🏆 Create Tournament", self._show_creator)
        self._add_sidebar_button(sidebar_layout, "manage", "📂 Manage Tournaments", self._show_manager)
        
        if self.test_mode:
            self._add_sidebar_button(sidebar_layout, "test", "🧪 Test Tournament", self._create_test_tournament)

        sidebar_layout.addStretch()
        
        # Version info at bottom of sidebar
        version_label = QLabel("v1.0 | FIDE Compliant")
        version_label.setObjectName("versionLabel")
        version_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(version_label)

        main_layout.addWidget(self.sidebar)

        # --- Main Content Area ---
        self.content_area = QStackedWidget()
        main_layout.addWidget(self.content_area)

        # 1. Home Page
        self.home_page = self._create_home_page()
        self.content_area.addWidget(self.home_page)

        # 2. Tournament Creator (Lazy loaded)
        self.tournament_creator_ui = None
        
        # 3. Tournament Manager (Lazy loaded)
        self.tournament_manager_ui = None

        logger.info("Main window UI initialized successfully")

    def _add_sidebar_button(self, layout, key, text, callback):
        """Helper to add styled buttons to the sidebar."""
        btn = QPushButton(text)
        btn.setObjectName("sidebarButton")
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.clicked.connect(callback)
        
        # Add tooltips based on key
        tooltips = {
            "home": "Go to the Home Dashboard",
            "create": "Create a new Tournament",
            "manage": "Manage existing Tournaments",
            "test": "Create a test tournament with dummy data"
        }
        if key in tooltips:
            btn.setToolTip(tooltips[key])
            
        layout.addWidget(btn)
        self.nav_buttons[key] = btn
        
        # Set Home as default checked
        if key == "home":
            btn.setChecked(True)

    def _create_home_page(self):
        """Creates the welcome/home page widget."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        welcome_label = QLabel("Welcome to Chess Tournament Manager")
        welcome_label.setObjectName("welcomeLabel")
        welcome_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_label)

        description_label = QLabel(
            "Create and manage chess tournaments with professional pairing systems.\n"
            "Select an option from the sidebar to get started."
        )
        description_label.setObjectName("descriptionLabel")
        description_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(description_label)

        return page

    def _show_home(self):
        """Switch to Home page."""
        self.content_area.setCurrentWidget(self.home_page)

    def _show_creator(self):
        """Switch to Tournament Creator page."""
        if self.tournament_creator_ui is None:
            self.tournament_creator_ui = TournamentCreatorUI(
                self.tournament_manager,
                self.player_manager,
                self.round_manager
            )
            self.content_area.addWidget(self.tournament_creator_ui)
        
        self.content_area.setCurrentWidget(self.tournament_creator_ui)

    def _show_manager(self):
        """Switch to Tournament Manager page."""
        if self.tournament_manager_ui is None:
            self.tournament_manager_ui = TournamentManagerUI(
                self.tournament_manager,
                self.player_manager,
                self.round_manager,
                self.team_manager
            )
            self.content_area.addWidget(self.tournament_manager_ui)
        
        self.content_area.setCurrentWidget(self.tournament_manager_ui)
        # Trigger refresh when switching to this tab
        if hasattr(self.tournament_manager_ui, 'show'):
             # We call show() on the widget to trigger any refresh logic it might have
             # (though in QStackedWidget it's already "shown", we might need a specific refresh method)
             # Looking at TournamentManagerUI, show() calls _refresh_tournament_list()
             self.tournament_manager_ui.show()

    def _load_stylesheet(self):
        """Load and apply the QSS stylesheet."""
        try:
            with open("src/ui/style.qss", "r") as f:
                self.setStyleSheet(f.read())
            logger.info("Stylesheet applied successfully.")
        except FileNotFoundError:
            logger.warning("Stylesheet file not found. Using default styles.")
        except Exception as e:
            logger.error(f"Error loading stylesheet: {e}")

    def _create_save_directory(self):
        """Ensure the save directory for tournaments exists."""
        save_dir = "saved_tournaments"
        try:
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
        except OSError as e:
            logger.error(f"Error creating save directory {save_dir}: {e}")

    def _create_test_tournament(self):
        """Create a test tournament with 7 players for development purposes."""
        logger.info("Creating test tournament")
        try:
            tournament_name = "Test Tournament"
            num_rounds = 3
            
            # Create tournament
            tournament_id = self.tournament_manager.create_tournament(
                tournament_name, datetime.date.today().isoformat(), num_rounds, "Dutch System", False
            )
            
            if tournament_id:
                # Create and register 7 players
                for i in range(1, 8):
                    player_name = str(i)
                    player_elo = 1000 + (i * 100)
                    self.player_manager.add_player(player_name, player_elo, tournament_id)
                
                # Create the first round pairings automatically
                self.round_manager.create_round_with_pairings(tournament_id, 1)
                
                QMessageBox.information(
                    self, "Test Tournament Created",
                    f"Test tournament '{tournament_name}' created successfully."
                )
                
                # Switch to manager to see it
                self.nav_buttons["manage"].click()
                
            else:
                QMessageBox.critical(self, "Error", "Failed to create test tournament.")
                
        except Exception as e:
            logger.error(f"Error creating test tournament: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create test tournament: {e}")
