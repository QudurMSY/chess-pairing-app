from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow
import sys

app = QApplication(sys.argv)
window = MainWindow()
window.show()

from PyQt5.QtCore import QTimer

def simulate_actions():
    try:
        window._show_creator()
        tc = window.tournament_creator_ui
        
        tc.tournament_name_input.setText("Test Tourney")
        tc.start_date_input.setText("2025-01-01")
        
        tc.player_name_input.setText("Alice")
        tc.player_surname_input.setText("Smith")
        tc.player_elo_input.setText("1500")
        tc._add_player_manually()
        
        tc.player_name_input.setText("Bob")
        tc.player_surname_input.setText("Jones")
        tc.player_elo_input.setText("1600")
        tc._add_player_manually()
        
        tc._create_tournament()
    except Exception as e:
        import traceback
        traceback.print_exc()
        
    app.quit()

QTimer.singleShot(500, simulate_actions)
sys.exit(app.exec_())
