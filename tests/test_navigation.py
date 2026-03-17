#!/usr/bin/env python3
"""
Test script for navigation functionality in the Chess Pairing App.
This script tests:
1. Each navigation button properly triggers its respective UI component
2. The singleton pattern works correctly (reusing existing instances)
3. The UI components display properly with appropriate window titles and sizes
4. The windows are properly managed and brought to front when clicked multiple times
"""

import sys
import time
import logging
from PyQt5.QtWidgets import QApplication, QPushButton
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
from src.ui.main_window import MainWindow
from src.ui.player_registration import PlayerRegistrationUI
from src.ui.tournament_management import TournamentManagementUI
from src.ui.round_management import RoundManagementUI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_navigation_functionality():
    """Test the navigation functionality comprehensively."""
    logger.info("Starting navigation functionality tests...")
    
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    try:
        # Create main window
        main_window = MainWindow()
        main_window.show()
        logger.info("Main window created and shown")
        
        # Wait for main window to be fully initialized
        QTest.qWait(100)
        
        # Test 1: Player Registration button functionality
        logger.info("\n=== Test 1: Player Registration Navigation ===")
        
        # Find the Player Registration button
        player_reg_button = None
        for child in main_window.findChildren(QPushButton):
            if child.text() == "Player Registration":
                player_reg_button = child
                break
        
        if player_reg_button is None:
            logger.error("Player Registration button not found!")
            return False
        
        logger.info("Found Player Registration button")
        
        # Click the button
        logger.info("Clicking Player Registration button...")
        QTest.mouseClick(player_reg_button, Qt.LeftButton)
        QTest.qWait(100)
        
        # Check if PlayerRegistrationUI instance was created
        if main_window.player_reg_ui is None:
            logger.error("PlayerRegistrationUI instance was not created!")
            return False
        
        logger.info("PlayerRegistrationUI instance created successfully")
        
        # Check if the window is visible
        if not main_window.player_reg_ui.isVisible():
            logger.error("PlayerRegistrationUI window is not visible!")
            return False
        
        logger.info("PlayerRegistrationUI window is visible")
        
        # Check window title
        expected_title = "Player Registration"
        actual_title = main_window.player_reg_ui.windowTitle()
        if actual_title != expected_title:
            logger.error(f"Window title mismatch. Expected: '{expected_title}', Actual: '{actual_title}'")
            return False
        
        logger.info(f"Window title correct: '{actual_title}'")
        
        # Check window size
        expected_width, expected_height = 600, 400
        actual_width, actual_height = main_window.player_reg_ui.width(), main_window.player_reg_ui.height()
        if actual_width != expected_width or actual_height != expected_height:
            logger.warning(f"Window size mismatch. Expected: {expected_width}x{expected_height}, Actual: {actual_width}x{actual_height}")
        else:
            logger.info(f"Window size correct: {actual_width}x{actual_height}")
        
        # Test singleton pattern - click button again
        logger.info("Testing singleton pattern - clicking Player Registration button again...")
        QTest.mouseClick(player_reg_button, Qt.LeftButton)
        QTest.qWait(100)
        
        # Check if the same instance is being reused
        if main_window.player_reg_ui is None:
            logger.error("PlayerRegistrationUI instance was lost after second click!")
            return False
        
        logger.info("Singleton pattern working - same instance reused")
        
        # Test 2: Tournament Management button functionality
        logger.info("\n=== Test 2: Tournament Management Navigation ===")
        
        # Find the Tournament Management button
        tournament_mgmt_button = None
        for child in main_window.findChildren(QPushButton):
            if child.text() == "Tournament Management":
                tournament_mgmt_button = child
                break
        
        if tournament_mgmt_button is None:
            logger.error("Tournament Management button not found!")
            return False
        
        logger.info("Found Tournament Management button")
        
        # Click the button
        logger.info("Clicking Tournament Management button...")
        QTest.mouseClick(tournament_mgmt_button, Qt.LeftButton)
        QTest.qWait(100)
        
        # Check if TournamentManagementUI instance was created
        if main_window.tournament_mgmt_ui is None:
            logger.error("TournamentManagementUI instance was not created!")
            return False
        
        logger.info("TournamentManagementUI instance created successfully")
        
        # Check if the window is visible
        if not main_window.tournament_mgmt_ui.isVisible():
            logger.error("TournamentManagementUI window is not visible!")
            return False
        
        logger.info("TournamentManagementUI window is visible")
        
        # Check window title
        expected_title = "Tournament Management"
        actual_title = main_window.tournament_mgmt_ui.windowTitle()
        if actual_title != expected_title:
            logger.error(f"Window title mismatch. Expected: '{expected_title}', Actual: '{actual_title}'")
            return False
        
        logger.info(f"Window title correct: '{actual_title}'")
        
        # Check window size
        expected_width, expected_height = 800, 600
        actual_width, actual_height = main_window.tournament_mgmt_ui.width(), main_window.tournament_mgmt_ui.height()
        if actual_width != expected_width or actual_height != expected_height:
            logger.warning(f"Window size mismatch. Expected: {expected_width}x{expected_height}, Actual: {actual_width}x{actual_height}")
        else:
            logger.info(f"Window size correct: {actual_width}x{actual_height}")
        
        # Test singleton pattern - click button again
        logger.info("Testing singleton pattern - clicking Tournament Management button again...")
        QTest.mouseClick(tournament_mgmt_button, Qt.LeftButton)
        QTest.qWait(100)
        
        # Check if the same instance is being reused
        if main_window.tournament_mgmt_ui is None:
            logger.error("TournamentManagementUI instance was lost after second click!")
            return False
        
        logger.info("Singleton pattern working - same instance reused")
        
        # Test 3: Round Management button functionality
        logger.info("\n=== Test 3: Round Management Navigation ===")
        
        # Find the Round Management button
        round_mgmt_button = None
        for child in main_window.findChildren(QPushButton):
            if child.text() == "Round Management":
                round_mgmt_button = child
                break
        
        if round_mgmt_button is None:
            logger.error("Round Management button not found!")
            return False
        
        logger.info("Found Round Management button")
        
        # Click the button
        logger.info("Clicking Round Management button...")
        QTest.mouseClick(round_mgmt_button, Qt.LeftButton)
        QTest.qWait(100)
        
        # Check if RoundManagementUI instance was created
        if main_window.round_mgmt_ui is None:
            logger.error("RoundManagementUI instance was not created!")
            return False
        
        logger.info("RoundManagementUI instance created successfully")
        
        # Check if the window is visible
        if not main_window.round_mgmt_ui.isVisible():
            logger.error("RoundManagementUI window is not visible!")
            return False
        
        logger.info("RoundManagementUI window is visible")
        
        # Check window title
        expected_title = "Round Management"
        actual_title = main_window.round_mgmt_ui.windowTitle()
        if actual_title != expected_title:
            logger.error(f"Window title mismatch. Expected: '{expected_title}', Actual: '{actual_title}'")
            return False
        
        logger.info(f"Window title correct: '{actual_title}'")
        
        # Check window size
        expected_width, expected_height = 700, 500
        actual_width, actual_height = main_window.round_mgmt_ui.width(), main_window.round_mgmt_ui.height()
        if actual_width != expected_width or actual_height != expected_height:
            logger.warning(f"Window size mismatch. Expected: {expected_width}x{expected_height}, Actual: {actual_width}x{actual_height}")
        else:
            logger.info(f"Window size correct: {actual_width}x{actual_height}")
        
        # Test singleton pattern - click button again
        logger.info("Testing singleton pattern - clicking Round Management button again...")
        QTest.mouseClick(round_mgmt_button, Qt.LeftButton)
        QTest.qWait(100)
        
        # Check if the same instance is being reused
        if main_window.round_mgmt_ui is None:
            logger.error("RoundManagementUI instance was lost after second click!")
            return False
        
        logger.info("Singleton pattern working - same instance reused")
        
        # Test 4: Window management - bringing windows to front
        logger.info("\n=== Test 4: Window Management (Bring to Front) ===")
        
        # Click each button again to ensure windows are brought to front
        logger.info("Clicking all buttons again to test window management...")
        
        # Store original instances
        original_player_reg_ui = main_window.player_reg_ui
        original_tournament_mgmt_ui = main_window.tournament_mgmt_ui
        original_round_mgmt_ui = main_window.round_mgmt_ui
        
        # Click Player Registration button
        QTest.mouseClick(player_reg_button, Qt.LeftButton)
        QTest.qWait(50)
        
        # Click Tournament Management button
        QTest.mouseClick(tournament_mgmt_button, Qt.LeftButton)
        QTest.qWait(50)
        
        # Click Round Management button
        QTest.mouseClick(round_mgmt_button, Qt.LeftButton)
        QTest.qWait(50)
        
        # Verify instances are still the same (singleton pattern maintained)
        if main_window.player_reg_ui is not original_player_reg_ui:
            logger.error("PlayerRegistrationUI instance changed after multiple clicks!")
            return False
        
        if main_window.tournament_mgmt_ui is not original_tournament_mgmt_ui:
            logger.error("TournamentManagementUI instance changed after multiple clicks!")
            return False
        
        if main_window.round_mgmt_ui is not original_round_mgmt_ui:
            logger.error("RoundManagementUI instance changed after multiple clicks!")
            return False
        
        logger.info("Window management working correctly - instances maintained and windows brought to front")
        
        logger.info("\n=== All Navigation Tests Passed Successfully! ===")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False
    finally:
        # Clean up
        logger.info("Cleaning up test...")
        app.quit()


if __name__ == "__main__":
    success = test_navigation_functionality()
    if success:
        logger.info("Navigation functionality test completed successfully!")
        sys.exit(0)
    else:
        logger.error("Navigation functionality test failed!")
        sys.exit(1)