"""
Varma Table implementation for Chess Pairing App.
Implements FIDE Varma Tables for restricted drawing of lots in Round Robin tournaments.
"""

from typing import List, Dict, Optional
import random
from collections import defaultdict
from src.database.database import Database

class VarmaTable:
    """
    Implements the Varma Table system for assigning pairing numbers.
    """

    def __init__(self, db: Database = None):
        self.db = db
        # Varma groupings based on number of players (9 to 24)
        # Sets A, B, C, D
        self.groupings = {
            9:  {'A': [3, 4, 8], 'B': [5, 7, 9], 'C': [1, 6], 'D': [2, 10]},
            10: {'A': [3, 4, 8], 'B': [5, 7, 9], 'C': [1, 6], 'D': [2, 10]},
            
            11: {'A': [4, 5, 9, 10], 'B': [1, 2, 7], 'C': [6, 8, 12], 'D': [3, 11]},
            12: {'A': [4, 5, 9, 10], 'B': [1, 2, 7], 'C': [6, 8, 12], 'D': [3, 11]},
            
            13: {'A': [4, 5, 6, 11, 12], 'B': [1, 2, 8, 9], 'C': [7, 10, 13], 'D': [3, 14]},
            14: {'A': [4, 5, 6, 11, 12], 'B': [1, 2, 8, 9], 'C': [7, 10, 13], 'D': [3, 14]},
            
            15: {'A': [5, 6, 7, 12, 13, 14], 'B': [1, 2, 3, 9, 10], 'C': [8, 11, 15], 'D': [4, 16]},
            16: {'A': [5, 6, 7, 12, 13, 14], 'B': [1, 2, 3, 9, 10], 'C': [8, 11, 15], 'D': [4, 16]},
            
            17: {'A': [5, 6, 7, 8, 14, 15, 16], 'B': [1, 2, 3, 10, 11, 12], 'C': [9, 13, 17], 'D': [4, 18]},
            18: {'A': [5, 6, 7, 8, 14, 15, 16], 'B': [1, 2, 3, 10, 11, 12], 'C': [9, 13, 17], 'D': [4, 18]},
            
            19: {'A': [6, 7, 8, 9, 15, 16, 17, 18], 'B': [1, 2, 3, 11, 12, 13, 14], 'C': [5, 10, 19], 'D': [4, 20]},
            20: {'A': [6, 7, 8, 9, 15, 16, 17, 18], 'B': [1, 2, 3, 11, 12, 13, 14], 'C': [5, 10, 19], 'D': [4, 20]},
            
            21: {'A': [6, 7, 8, 9, 10, 17, 18, 19, 20], 'B': [1, 2, 3, 4, 12, 13, 14, 15], 'C': [11, 16, 21], 'D': [5, 22]},
            22: {'A': [6, 7, 8, 9, 10, 17, 18, 19, 20], 'B': [1, 2, 3, 4, 12, 13, 14, 15], 'C': [11, 16, 21], 'D': [5, 22]},
            
            23: {'A': [6, 7, 8, 9, 10, 11, 19, 20, 21, 22], 'B': [1, 2, 3, 4, 13, 14, 15, 16, 17], 'C': [12, 18, 23], 'D': [5, 24]},
            24: {'A': [6, 7, 8, 9, 10, 11, 19, 20, 21, 22], 'B': [1, 2, 3, 4, 13, 14, 15, 16, 17], 'C': [12, 18, 23], 'D': [5, 24]},
        }

    def assign_pairing_numbers(self, players: List[Dict], tournament_id: int) -> List[Dict]:
        """
        Assign pairing numbers to players based on Varma Table rules.
        Updates the players list in-place and updates the database.
        """
        num_players = len(players)
        
        # Check if number of players is within supported range (9-24)
        # If not, we can't use Varma. Fallback to random or rating order?
        # FIDE says Varma is for 9-24.
        if num_players < 9 or num_players > 24:
            # Fallback: Just assign 1..N based on current order (which might be rating/score)
            # Or shuffle? FIDE standard is drawing of lots for Berger.
            # We'll just assign sequentially for now as fallback.
            print(f"Varma Table: Number of players {num_players} not supported (9-24). Using sequential assignment.")
            for i, player in enumerate(players):
                player['pairing_number'] = i + 1
                if self.db:
                    self.db.update_player_pairing_number(player['id'], i + 1)
            return players

        # Get the sets for this number of players
        # Deep copy to modify
        varma_sets = {k: v[:] for k, v in self.groupings[num_players].items()}
        
        # Group players by Federation
        by_federation = defaultdict(list)
        for p in players:
            fed = p.get('federation', 'UNK')
            by_federation[fed].append(p)
            
        # Sort federations:
        # 1. By count (descending)
        # 2. By code (alphabetical)
        sorted_feds = sorted(by_federation.items(), key=lambda x: (-len(x[1]), x[0]))
        
        # Available envelopes (keys of varma_sets)
        # We assume envelopes are "available" if they have numbers left.
        
        for fed_code, fed_players in sorted_feds:
            # Sort players within federation alphabetically by name (FIDE rule)
            fed_players.sort(key=lambda p: p['name'])
            
            remaining_players = fed_players[:]
            
            while remaining_players:
                count_needed = len(remaining_players)
                
                # Find valid sets (sets with enough remaining numbers)
                valid_sets = [k for k, v in varma_sets.items() if len(v) >= count_needed]
                
                if valid_sets:
                    # Pick one set (simulate drawing a large envelope)
                    # We can pick randomly among valid sets
                    chosen_set_key = random.choice(valid_sets)
                    chosen_set = varma_sets[chosen_set_key]
                    
                    # Draw numbers from this set for all remaining players
                    # "draw one number from the small envelopes inside"
                    # We simulate this by shuffling the available numbers in the set
                    # and popping required amount.
                    # Or just picking random sample.
                    
                    # We need to remove them from the set so they aren't used again
                    # But actually we pick specific numbers.
                    
                    # Shuffle the set to simulate random drawing
                    random.shuffle(chosen_set)
                    
                    # Assign numbers
                    for _ in range(count_needed):
                        p = remaining_players.pop(0)
                        num = chosen_set.pop(0)
                        p['pairing_number'] = num
                        if self.db:
                            self.db.update_player_pairing_number(p['id'], num)
                            
                else:
                    # No set fits all remaining players!
                    # Fallback: Pick the set with MOST available numbers to maximize grouping
                    # and split the federation across sets.
                    
                    # Filter sets that have AT LEAST 1 number
                    available_sets = [k for k, v in varma_sets.items() if len(v) > 0]
                    
                    if not available_sets:
                        raise ValueError("Run out of pairing numbers! Logic error.")
                        
                    # Find set with max available
                    best_set_key = max(available_sets, key=lambda k: len(varma_sets[k]))
                    best_set = varma_sets[best_set_key]
                    
                    # Take as many as possible
                    available_count = len(best_set)
                    
                    random.shuffle(best_set)
                    
                    for _ in range(available_count):
                        if not remaining_players:
                            break
                        p = remaining_players.pop(0)
                        num = best_set.pop(0)
                        p['pairing_number'] = num
                        if self.db:
                            self.db.update_player_pairing_number(p['id'], num)
                    
                    # Continue loop to assign remaining players to next best set
                    
        return players
