import csv
from typing import List, Dict, Any
from src.database.database import Database
from src.core.tie_break import TieBreak

class ReportGenerator:
    """Generates reports for the tournament."""

    def __init__(self, db: Database):
        self.db = db
        self.tie_break = TieBreak(db)

    def generate_standings_report(self, tournament_id: int) -> List[Dict[str, Any]]:
        """
        Generates a standings report for a tournament.
        Returns a list of dictionaries containing player standings.
        """
        # TieBreak.calculate_tie_breaks returns standings sorted by Score, Buchholz, SB
        standings = self.tie_break.calculate_tie_breaks(tournament_id)
        
        # Add rank
        for i, player in enumerate(standings):
            player['rank'] = i + 1
            
        return standings

    def generate_pairings_report(self, tournament_id: int, round_number: int) -> List[Dict[str, Any]]:
        """
        Generates a pairings report for a specific round.
        Returns a list of dictionaries containing pairings.
        """
        rounds = self.db.get_rounds(tournament_id)
        # Find the round ID for the given round number
        target_round = next((r for r in rounds if r['round_number'] == round_number), None)
        
        if not target_round:
            return []

        results = self.db.get_results(target_round['id'])
        pairings_report = []
        
        for result in results:
            player1_name = self._get_player_name(result['player1_id'])
            player2_name = self._get_player_name(result['player2_id']) if result['player2_id'] else "BYE"
            
            # Determine White and Black
            if result['player1_color'] == 'W':
                white = player1_name
                black = player2_name
            elif result['player2_color'] == 'W':
                white = player2_name
                black = player1_name
            else:
                # Fallback if colors are not set (should not happen in valid pairings)
                white = player1_name
                black = player2_name

            result_str = "*"  # Default
            if result['is_bye']:
                result_str = "1-0 (Bye)"
            elif result['winner_id'] is not None:
                if result['winner_id'] == 0:
                    result_str = "1/2-1/2"
                elif result['winner_id'] == result['player1_id']:
                     if result['player1_color'] == 'W':
                         result_str = "1-0"
                     else:
                         result_str = "0-1"
                elif result['winner_id'] == result['player2_id']:
                     if result['player2_color'] == 'W':
                         result_str = "1-0"
                     else:
                         result_str = "0-1"
            
            pairings_report.append({
                "table": result.get('id', 0), # Using result ID as makeshift table number if not available
                "white": white,
                "black": black,
                "result": result_str
            })
            
        return pairings_report

    def _get_player_name(self, player_id: int) -> str:
        """Helper to get player name by ID."""
        self.db.cursor.execute("SELECT name FROM Players WHERE id = ?", (player_id,))
        res = self.db.cursor.fetchone()
        return res[0] if res else "Unknown"

    def export_to_csv(self, data: List[Dict[str, Any]], filename: str, fieldnames: List[str]):
        """Exports data to a CSV file."""
        with open(filename, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                # Filter row to only include keys in fieldnames to avoid ValueErrors
                filtered_row = {k: row.get(k, '') for k in fieldnames}
                writer.writerow(filtered_row)

    def export_to_text(self, data: List[Dict[str, Any]], filename: str, headers: Dict[str, str], format_str: str):
        """
        Exports data to a text file.
        format_str should be a format string like "{rank:<4} {name:<20} {score:<5}"
        headers should be a dict mapping keys to display names, e.g. {"rank": "Rank", "name": "Name"}
        """
        with open(filename, mode='w', encoding='utf-8') as txtfile:
            # Write headers
            txtfile.write(format_str.format(**headers) + "\n")
            txtfile.write("-" * 80 + "\n")
            
            for row in data:
                # Ensure all keys in format_str are present in row
                # We might need to handle missing keys or type conversions
                safe_row = {k: str(v) for k, v in row.items()}
                try:
                    txtfile.write(format_str.format(**safe_row) + "\n")
                except KeyError as e:
                    print(f"KeyError in export_to_text: {e}")
