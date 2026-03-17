import unittest
import re
from unittest.mock import MagicMock
from src.core.pairing.swiss_pairing import SwissPairing

class TestFideDutchPairing(unittest.TestCase):
    def test_first_round_pairing(self):
        players = self.load_players("trial_tournament.txt")
        
        mock_db = MagicMock()
        mock_db.get_players_with_bye.return_value = []
        mock_db.get_player_color_history.return_value = []
        mock_db.get_player_float_history.return_value = []
        mock_db.get_tournament_settings.return_value = {"initial_color": "W"}
        mock_db.get_rounds.return_value = []

        pairing_system = SwissPairing(db=mock_db, tournament_id=1, round_number=1, players=players)
        generated_pairings, bye_player = pairing_system.pair_round()
        
        expected_pairings = self.load_expected_pairings("expected_pairings.txt")
        
        # Create a dictionary to look up player details by ID
        player_dict = {p["id"]: p for p in players}
        
        # Normalize generated pairings to (p1_name, p1_rating), (p2_name, p2_rating) format
        normalized_generated = []
        for p1_id, p2_id, _ in generated_pairings:
            p1 = player_dict[p1_id]
            p2 = player_dict[p2_id]
            normalized_generated.append(((p1["name"], p1["rating"]), (p2["name"], p2["rating"])))
            
        if bye_player:
            bye_p_details = player_dict[bye_player]
            normalized_generated.append(((bye_p_details["name"], bye_p_details["rating"]), None))

        self.assertEqual(len(normalized_generated), len(expected_pairings), "Number of pairings should be equal")

        # More robust comparison
        expected_set = {tuple(sorted(p)) if p[1] is not None else p for p in expected_pairings}
        generated_set = {
            tuple(sorted(((p1_name, p1_rating), (p2_name, p2_rating)))) if p2_name is not None else ((p1_name, p1_rating), None)
            for (p1_name, p1_rating), (p2_name, p2_rating) in normalized_generated
        }
        self.assertEqual(generated_set, expected_set, "Pairings do not match expected pairings")

    def load_players(self, filename):
        players_data = []
        with open(filename, "r") as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                
                parts = line.strip().split('\t')
                
                if len(parts) == 3:
                    first_name, last_name, rating_str = parts
                    name = f"{last_name}, {first_name}"
                    rating = int(rating_str)
                elif len(parts) == 2:
                    name_str, rating_str = parts
                    name_parts = name_str.split()
                    last_name = name_parts[-1]
                    first_name = " ".join(name_parts[:-1])
                    name = f"{last_name}, {first_name}"
                    rating = int(rating_str)
                else:
                    space_parts = line.strip().split()
                    rating = int(space_parts[-1])
                    name_parts = space_parts[:-1]
                    last_name = name_parts[-1]
                    first_name = " ".join(name_parts[:-1])
                    name = f"{last_name}, {first_name}"
                
                players_data.append({"name": name, "rating": rating, "score": 0})

        players_data.sort(key=lambda p: (-p['rating'], p['name']))
        
        players = []
        for i, p_data in enumerate(players_data):
            players.append({"id": i + 1, **p_data})
            
        return players

    def load_expected_pairings(self, filename):
        pairings = []
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                result_match = re.search(r"\s+(1 - 0|0 - 1|1/2 - 1/2)\s+", line)
                if not result_match:
                    continue

                p1_str = line[:result_match.start()].strip()
                p2_str = line[result_match.end():].strip()

                def extract_player_info(player_str):
                    parts = player_str.split()
                    
                    # Remove categories like U14, S50
                    parts_no_cat = [p for p in parts if not re.match(r"^[US]\d+$", p)]
                    
                    if len(parts_no_cat) < 2:
                        return None, None
                        
                    rating = int(parts_no_cat[-2])
                    
                    # Find where the name starts
                    name_start_index = 0
                    for i, part in enumerate(parts_no_cat):
                        if not part.isdigit():
                            name_start_index = i
                            break

                    rating_index = len(parts_no_cat) - 2
                    name = " ".join(parts_no_cat[name_start_index:rating_index])
                    return name, rating

                p1_name, p1_rating = extract_player_info(p1_str)
                p2_name, p2_rating = extract_player_info(p2_str)
                
                if p1_name and p2_name:
                    pairings.append(((p1_name, p1_rating), (p2_name, p2_rating)))
                
        return pairings

if __name__ == "__main__":
    unittest.main()
