"""
Team pairing module for the Chess Pairing App.
This module implements the Swiss Team Pairing System.
"""

from typing import List, Dict, Tuple
from src.database.database import Database


class TeamPairing:
    """Implements the Swiss Team Pairing System."""

    def __init__(self, db: Database):
        """Initialize the TeamPairing with a database connection."""
        self.db = db

    def get_team_standings(self, tournament_id: int) -> List[Dict]:
        """Calculate match points and game points for all teams."""
        teams = self.db.get_teams(tournament_id)
        
        for team in teams:
            team['match_points'] = 0.0
            team['game_points'] = 0.0
            
            # Get all matches for this team
            self.db.cursor.execute(
                """
                SELECT team1_id, team2_id, match_points_team1, match_points_team2,
                       game_points_team1, game_points_team2
                FROM TeamMatches
                WHERE tournament_id = ? AND (team1_id = ? OR team2_id = ?)
                """, (tournament_id, team['id'], team['id'])
            )
            matches = self.db.cursor.fetchall()
            
            for match in matches:
                if match[0] == team['id']:
                    team['match_points'] += match[2] if match[2] is not None else 0
                    team['game_points'] += match[4] if match[4] is not None else 0
                else:
                    team['match_points'] += match[3] if match[3] is not None else 0
                    team['game_points'] += match[5] if match[5] is not None else 0
                    
        # Sort teams by Match Points (descending), then Game Points (descending), then Seed Ranking (ascending), then Team Name (ascending)
        teams.sort(key=lambda x: (-x['match_points'], -x['game_points'], x.get('seed_ranking') or 999, x['name']))
        return teams

    def pair_teams(self, tournament_id: int, round_number: int) -> List[Tuple[int, int]]:
        """Pair teams for a round using Match Points and Game Points."""
        # Get standings
        teams = self.get_team_standings(tournament_id)
        
        # Pair teams
        pairings = []
        for i in range(0, len(teams), 2):
            if i + 1 < len(teams):
                pairings.append((teams[i]['id'], teams[i + 1]['id']))
        
        return pairings

    def assign_colors(self, tournament_id: int, round_number: int) -> Dict[int, str]:
        """Assign colors to teams for a round."""
        # Get all rounds for previous rounds
        previous_rounds = self.db.get_rounds(tournament_id)
        previous_rounds = [r for r in previous_rounds if r['round_number'] < round_number]
        
        # Initialize color assignments
        color_assignments = {}
        
        # Assign colors based on previous color assignments
        for r in previous_rounds:
            results = self.db.get_team_results(r['id'])
            for result in results:
                team1_id = result['team1_id']
                team2_id = result['team2_id']
                
                # Assign colors alternately
                if team1_id not in color_assignments:
                    color_assignments[team1_id] = "White"
                else:
                    color_assignments[team1_id] = "Black" if color_assignments[team1_id] == "White" else "White"
                
                if team2_id not in color_assignments:
                    color_assignments[team2_id] = "Black"
                else:
                    color_assignments[team2_id] = "White" if color_assignments[team2_id] == "Black" else "Black"
        
        return color_assignments

    def handle_bye(self, tournament_id: int, round_number: int) -> int:
        """Handle bye assignment for a round."""
        # Get all teams for the tournament, sorted by standings
        teams = self.get_team_standings(tournament_id)
        
        # If the number of teams is odd, assign a bye
        if len(teams) % 2 != 0:
            # Assign bye to the team with the lowest score/points
            # Since get_team_standings sorts descending by points, the lowest is at the end
            return teams[-1]['id']
        
        return None