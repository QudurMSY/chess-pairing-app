#!/usr/bin/env python3
"""
Test script for large tournaments in the Chess Pairing App.
This script tests the app with a large dataset (256+ players).
"""

import sys
import time
from src.database.database import Database
from src.core.player_manager import PlayerManager
from src.core.tournament_manager import TournamentManager
from src.core.round_manager import RoundManager


def test_large_tournament():
    """Test the app with a large tournament (256 players)."""
    print("Testing Large Tournament (256 players)...")
    
    db = Database(":memory:")
    player_manager = PlayerManager(db)
    tournament_manager = TournamentManager(db)
    round_manager = RoundManager(db, tournament_manager)
    
    # Create a tournament
    tournament_id = tournament_manager.create_tournament(
        "Large Swiss Test Tournament", "2026-01-27", 8, "Swiss", False
    )
    
    # Add 256 players
    start_time = time.time()
    player_ids = []
    for i in range(1, 257):
        player_id = player_manager.add_player(f"Player {i}", 1500 + i * 10, tournament_id)
        player_ids.append(player_id)
    
    print(f"Added 256 players in {time.time() - start_time:.2f} seconds")
    
    # Create round 1 with pairings
    start_time = time.time()
    round_id_1 = round_manager.create_round_with_pairings(tournament_id, 1)
    pairings_round_1 = round_manager.get_round_results(round_id_1)
    print(f"Generated {len(pairings_round_1)} pairings in {time.time() - start_time:.2f} seconds")
    
    db.close()
    print("Large Tournament Test Completed.\n")


if __name__ == "__main__":
    test_large_tournament()
    
    print("Large tournament test completed successfully!")