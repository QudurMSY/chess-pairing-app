#!/usr/bin/env python3
"""
Main entry point for the Chess Pairing App.
This script initializes the application and launches the main window.
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.memory.memory_bank import MemoryBank

logger = logging.getLogger(__name__)
logger.debug("Application started")

def main():
    """Main function to launch the Chess Pairing App."""
    app = QApplication(sys.argv)
    # Initialize memory bank
    memory_bank = MemoryBank()
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()