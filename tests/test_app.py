#!/usr/bin/env python3
"""
Test script for the Chess Pairing App.
This script tests the app with sample data for all systems.
"""

import sys
from src.database.database import Database
from src.core.player_manager import PlayerManager
from src.core.tournament_manager import TournamentManager
from src.core.round_manager import RoundManager
from src.core.team_manager import TeamManager
from src.core.pairing.swiss_pairing import SwissPairing
from src.core.pairing.berger_table import BergerTable
from src.core.pairing.burstein_system import BursteinSystem
from src.core.pairing.dubov_system import DubovSystem
from src.core.pairing.lim_system import LimSystem
from src.core.pairing.double_swiss_system import DoubleSwissSystem
from src.core.tie_break import TieBreak


def test_swiss_pairing():
    """Test the Swiss pairing system."""
    print("Testing Swiss Pairing System...")
    
    db = Database(":memory:")
    player_manager = PlayerManager(db)
    tournament_manager = TournamentManager(db)
    round_manager = RoundManager(db, tournament_manager)
    
    # Create a tournament
    tournament_id = tournament_manager.create_tournament(
        "Swiss Test Tournament", "2026-01-27", 5, "Swiss", False
    )
    
    # Add players
    player_ids = []
    for i in range(1, 9):
        player_id = player_manager.add_player(f"Player {i}", 1500 + i * 100, tournament_id)
        player_ids.append(player_id)
    
    # Create round 1 with pairings
    round_id_1 = round_manager.create_round_with_pairings(tournament_id, 1)
    pairings_round_1 = round_manager.get_round_results(round_id_1)
    print(f"Round 1 Pairings: {pairings_round_1}")
    
    # No need to explicitly assign colors or handle bye in this test as it's part of create_round_with_pairings
    
    db.close()
    print("Swiss Pairing System Test Completed.\n")


def test_berger_table():
    """Test the Berger table system."""
    print("Testing Berger Table System...")
    
    db = Database(":memory:")
    player_manager = PlayerManager(db)
    tournament_manager = TournamentManager(db)
    round_manager = RoundManager(db, tournament_manager)
    
    # Create a tournament
    tournament_id = tournament_manager.create_tournament(
        "Berger Test Tournament", "2026-01-27", 5, "Berger Table", False
    )
    
    # Add players
    player_ids = []
    for i in range(1, 9):
        player_id = player_manager.add_player(f"Player {i}", 1500 + i * 100, tournament_id)
        player_ids.append(player_id)
    
    # Generate pairings for round 1
    round_id_1 = round_manager.create_round_with_pairings(tournament_id, 1)
    pairings_round_1 = round_manager.get_round_results(round_id_1)
    print(f"Round 1 Pairings: {pairings_round_1}")
    
    # To test rotation for round 2, we need to complete round 1 first.
    # For simplicity, we'll manually add some results for round 1 if needed to test round 2 generation later.
    # For now, we focus on the initial pairing generation.
    
    db.close()
    print("Berger Table System Test Completed.\n")


def test_tie_break():
    """Test the tie-break systems."""
    print("Testing Tie-Break Systems...")
    
    db = Database(":memory:")
    player_manager = PlayerManager(db)
    tournament_manager = TournamentManager(db)
    round_manager = RoundManager(db, tournament_manager)
    tie_break = TieBreak(db)
    
    # Create a tournament
    tournament_id = tournament_manager.create_tournament(
        "Tie-Break Test Tournament", "2026-01-27", 5, "Swiss", False
    )
    
    # Add players
    player_ids = []
    for i in range(1, 5):
        player_id = player_manager.add_player(f"Player {i}", 1500 + i * 100, tournament_id)
        player_ids.append(player_id)
    
    # Create rounds and record results
    for round_num in range(1, 4):
        round_id = round_manager.create_round(tournament_id, round_num)
        
        # Record some results
        if round_num == 1:
            round_manager.record_result(round_id, player_ids[0], player_ids[1], player_ids[0], False)
            round_manager.record_result(round_id, player_ids[2], player_ids[3], player_ids[2], False)
        elif round_num == 2:
            round_manager.record_result(round_id, player_ids[0], player_ids[2], player_ids[0], False)
            round_manager.record_result(round_id, player_ids[1], player_ids[3], player_ids[1], False)
        elif round_num == 3:
            round_manager.record_result(round_id, player_ids[0], player_ids[3], player_ids[0], False)
            round_manager.record_result(round_id, player_ids[1], player_ids[2], player_ids[1], False)
    
    # Calculate Buchholz scores
    for player_id in player_ids:
        buchholz_score = tie_break.buchholz(tournament_id, player_id)
        print(f"Player {player_id} Buchholz Score: {buchholz_score}")
    
    # Calculate Sonneborn-Berger scores
    for player_id in player_ids:
        sb_score = tie_break.sonneborn_berger(tournament_id, player_id)
        print(f"Player {player_id} Sonneborn-Berger Score: {sb_score}")
    
    # Calculate direct encounter
    de_score = tie_break.direct_encounter(tournament_id, player_ids[0], player_ids[1])
    print(f"Direct Encounter between Player {player_ids[0]} and Player {player_ids[1]}: {de_score}")
    
    db.close()
    print("Tie-Break Systems Test Completed.\n")


if __name__ == "__main__":
    test_swiss_pairing()
    test_berger_table()
    test_tie_break()
    
    print("All tests completed successfully!")