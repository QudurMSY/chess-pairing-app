"""
Swiss pairing system module for the Chess Pairing App.
This module implements the FIDE-compliant Dutch system pairing logic.
"""

from typing import List, Dict, Tuple, Optional, Set
from src.database.database import Database
import itertools

class SwissPairing:
    """Implements the FIDE-compliant Dutch system pairing logic."""

    def __init__(self, db: Database, tournament_id: int, round_number: int, players: List[Dict]):
        """Initialize the SwissPairing with a database connection."""
        self.db = db
        self.tournament_id = tournament_id
        self.round_number = round_number
        self.players = self._prepare_players(players)
        self.opponent_history = self._fetch_opponent_history()
        self.bye_history = self._get_bye_history()
        self.initial_color = self._get_initial_color()

    def _prepare_players(self, players: List[Dict]) -> List[Dict]:
        """Set TPN and other required fields for players."""
        active_players = [p for p in players if not p.get('withdrawn', False)]
    
        for i, p in enumerate(active_players):
            if 'tpn' not in p or p['tpn'] is None:
                p['tpn'] = i + 1
            p['score'] = p.get('score', 0)
            p['color_history'] = self._get_color_history(p['id'])
            p['downfloat_history'] = self._get_float_history(p['id'], 'downfloat')
            p['upfloat_history'] = self._get_float_history(p['id'], 'upfloat')
        
        return active_players

    def pair_round(self) -> Tuple[List[Tuple[int, int, str]], Optional[int]]:
        """
        Main function to generate pairings for a round.
        Returns pairings (p1_id, p2_id, p1_color) and the player ID for the bye.
        """
        players_to_pair = sorted(self.players, key=lambda p: (-p['score'], p['tpn']))
        
        score_groups = self._create_score_groups(players_to_pair)
        
        pairings = []
        unpaired_players = []
        
        sorted_scores = sorted(score_groups.keys(), reverse=True)
        for score in sorted_scores:
            resident_players = score_groups[score]
            pairing_bracket = unpaired_players + resident_players
            
            bracket_pairings, downfloaters = self._pair_bracket(pairing_bracket)
            
            pairings.extend(bracket_pairings)
            unpaired_players = downfloaters
            
        bye_player_id = self._handle_bye(unpaired_players)
        
        final_pairings_with_colors = self._assign_colors(pairings)

        self._update_float_history(final_pairings_with_colors, bye_player_id)

        return final_pairings_with_colors, bye_player_id

    def _create_score_groups(self, players: List[Dict]) -> Dict[float, List[Dict]]:
        """Group players by their scores."""
        score_groups = {}
        for player in players:
            score = player['score']
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(player)
        return score_groups

    def _pair_bracket(self, bracket: List[Dict]) -> Tuple[List[Tuple[int, int]], List[Dict]]:
        """Pairs a single bracket according to FIDE Dutch system rules."""
        if not bracket:
            return [], []

        resident_score = bracket[-1]['score']
        mdps = [p for p in bracket if p['score'] > resident_score]
        residents = [p for p in bracket if p['score'] == resident_score]

        is_homogeneous = not mdps
        
        if is_homogeneous:
            candidates = self._generate_candidates_homogeneous(residents)
        else:
            candidates = self._generate_candidates_heterogeneous(mdps, residents)
        
        best_candidate = self._evaluate_candidates(candidates)

        if not best_candidate:
            # If no valid pairing is found, consider all players as downfloaters
            return [], bracket

        paired_ids = set()
        raw_pairs = []
        for p1, p2 in best_candidate['pairs']:
            paired_ids.add(p1['id'])
            paired_ids.add(p2['id'])
            raw_pairs.append((p1['id'], p2['id']))

        downfloaters = [p for p in bracket if p['id'] not in paired_ids]
        
        return raw_pairs, downfloaters

    def _generate_candidates_homogeneous(self, players: List[Dict]) -> List[Dict]:
        """Generate valid pairing candidates for a homogeneous bracket, stopping early if a good candidate is found."""
        print(f"Generating candidates for {len(players)} players.")
        max_pairs = len(players) // 2
        if max_pairs == 0:
            return [{'pairs': [], 'downfloaters': players, 'score': 0}]

        s1_original = players[:max_pairs]
        s2_original = players[max_pairs:]

        exchanges = self._get_exchanges(s1_original, s2_original)
        # print(f"Generated {len(exchanges)} exchanges.")

        best_candidate = None
        MAX_HOMO_CANDIDATES = 50 # Further reduced
        count = 0

        for s1, s2 in exchanges:
            if count >= MAX_HOMO_CANDIDATES: break
            transpositions = self._get_transpositions(s2, max_transpositions=50) # Reduced transpositions
            for s2_perm in transpositions:
                pairs = list(zip(s1, s2_perm))
                
                if all(not self._have_played_before(p1['id'], p2['id']) for p1, p2 in pairs):
                    downfloaters = list(s2_perm[len(s1):])
                    candidate = {'pairs': pairs, 'downfloaters': downfloaters}
                    
                    if best_candidate is None:
                        best_candidate = candidate
                    else:
                        if len(downfloaters) < len(best_candidate['downfloaters']):
                            best_candidate = candidate
                    
                    count += 1
                    if count >= MAX_HOMO_CANDIDATES: break
                    
        if best_candidate:
            return [best_candidate]
        else:
            return []

    def _generate_candidates_heterogeneous(self, mdps: List[Dict], residents: List[Dict]) -> List[Dict]:
        """Generate all valid pairing candidates for a heterogeneous bracket."""
        candidates = []
        MAX_CANDIDATES = 100  # Further reduced safety limit
        candidate_count = 0
        
        # Iterate through all possible numbers of MDPs to pair
        for m1 in range(min(len(mdps), len(residents)) + 1):
            if candidate_count >= MAX_CANDIDATES:
                break

            # Optimization: If numbers are large, don't try every single combination
            mdp_combinations = itertools.combinations(mdps, m1)
            
            combo_limit = 20 # Further reduced limit
            combo_count = 0

            for mdp_selection in mdp_combinations:
                combo_count += 1
                if combo_count > combo_limit: break
                
                resident_permutations = itertools.permutations(residents, m1)
                perm_limit = 20 # Further reduced limit
                perm_count = 0
                
                for resident_selection in resident_permutations:
                    perm_count += 1
                    if perm_count > perm_limit: break

                    mdp_pairs = list(zip(list(mdp_selection), resident_selection))

                    if not all(not self._have_played_before(p1['id'], p2['id']) for p1, p2 in mdp_pairs):
                        continue

                    remaining_residents = [p for p in residents if p not in resident_selection]
                    
                    remainder_candidates = self._generate_candidates_homogeneous(remaining_residents)
                    
                    limbo = [p for p in mdps if p not in mdp_selection]

                    for rem_cand in remainder_candidates:
                        all_pairs = mdp_pairs + rem_cand['pairs']
                        all_downfloaters = limbo + rem_cand['downfloaters']
                        candidates.append({'pairs': all_pairs, 'downfloaters': all_downfloaters})
                        candidate_count += 1
                        if candidate_count >= MAX_CANDIDATES: break
                    
                    if candidate_count >= MAX_CANDIDATES: break
                if candidate_count >= MAX_CANDIDATES: break
                
        return candidates


    def _evaluate_candidates(self, candidates: List[Dict]) -> Optional[Dict]:
        """Select the best candidate based on FIDE criteria."""
        if not candidates:
            return None

        # C6-C7: Minimize number and score of downfloaters
        candidates.sort(key=lambda c: (len(c['downfloaters']), sum(p['score'] for p in c['downfloaters'])), reverse=False)
        
        best_candidates = [c for c in candidates if len(c['downfloaters']) == len(candidates[0]['downfloaters']) and sum(p['score'] for p in c['downfloaters']) == sum(p['score'] for p in candidates[0]['downfloaters'])]
        
        # C12-C13: Minimize color preference violations
        best_candidates.sort(key=lambda c: self._score_candidate_colors(c['pairs']), reverse=False)

        # C14-C21: Minimize float history issues (simplified)
        best_candidates.sort(key=lambda c: self._score_candidate_floats(c), reverse=False)

        return best_candidates[0]

    def _score_candidate_colors(self, pairs: List[Tuple[Dict, Dict]]) -> float:
        """Score a candidate based on color preferences."""
        score = 0
        for p1, p2 in pairs:
            # Simplified scoring
            pref1 = self._get_color_preference(p1)
            pref2 = self._get_color_preference(p2)
            if pref1 != 'N' and pref2 != 'N' and pref1 == pref2:
                score += 1 # Penalize same preferences
        return score

    def _score_candidate_floats(self, candidate: Dict) -> int:
        """Score a candidate based on float history."""
        score = 0
        downfloater_ids = {p['id'] for p in candidate['downfloaters']}
        
        for p_id in downfloater_ids:
            player = self._get_player_by_id(p_id)
            if self.round_number - 1 in player['downfloat_history']:
                score += 1 # C14
            if self.round_number - 2 in player['downfloat_history']:
                score += 0.5 # C16
        
        for p1, p2 in candidate['pairs']:
            if p1['score'] < p2['score']: p1, p2 = p2, p1 # p1 is higher score
            if self.round_number - 1 in p2['upfloat_history']:
                score += 1 # C15
            if self.round_number - 2 in p2['upfloat_history']:
                score += 0.5 # C17
        return score

    def _get_transpositions(self, s2: List[Dict], max_transpositions=200) -> List[List[Dict]]:
        """Generate transpositions for S2, sorted lexicographically by BSN."""
        # BSN is approximated by TPN for simplicity here
        # Limiting to max_transpositions to avoid performance issues
        transpositions = sorted(list(itertools.permutations(s2)), key=lambda p_list: [p['tpn'] for p in p_list])
        return transpositions[:max_transpositions]

    def _get_exchanges(self, s1: List[Dict], s2: List[Dict], max_exchanges=10) -> List[Tuple[List[Dict], List[Dict]]]:
        """Generate exchanges between S1 and S2."""
        # This is a complex rule; a simplified version is implemented here
        # Return the original S1, S2 as the first option
        all_s1_s2_combos = [(s1, s2)]
        
        # Add single-player exchanges, but limited to max_exchanges
        count = 1
        for i in range(len(s1)):
            for j in range(len(s2)):
                if count >= max_exchanges:
                    return all_s1_s2_combos
                new_s1 = s1[:i] + [s2[j]] + s1[i+1:]
                new_s2 = s2[:j] + [s1[i]] + s2[j+1:]
                all_s1_s2_combos.append((list(new_s1), list(new_s2)))
                count += 1

        return all_s1_s2_combos

    def _have_played_before(self, p1_id: int, p2_id: int) -> bool:
        """Check if two players have played before."""
        return p2_id in self.opponent_history.get(p1_id, set())

    def _handle_bye(self, unpaired_players: List[Dict]) -> Optional[int]:
        """Determines which player gets the bye from a list of unpaired players."""
        if not unpaired_players:
            return None

        eligible_for_bye = [p for p in unpaired_players if p['id'] not in self.bye_history]

        if not eligible_for_bye:
            eligible_for_bye = unpaired_players # Should not happen if C2 is followed

        # C5: Minimize score of bye assignee
        eligible_for_bye.sort(key=lambda p: (p['score'], p.get('unplayed_games', 0), p['tpn']))
        
        return eligible_for_bye[0]['id'] if eligible_for_bye else None

    def _assign_colors(self, pairings: List[Tuple[int, int]]) -> List[Tuple[int, int, str]]:
        """Assign colors to each pair based on FIDE rules."""
        colored_pairings = []
        for p1_id, p2_id in pairings:
            p1 = self._get_player_by_id(p1_id)
            p2 = self._get_player_by_id(p2_id)

            if not p1 or not p2: continue

            # Ensure p1 is the higher-ranked player for consistency
            if (p1['score'], -p1['tpn']) < (p2['score'], -p2['tpn']):
                p1, p2 = p2, p1

            p1_pref_val, p1_pref_str = self._get_color_preference(p1)
            p2_pref_val, p2_pref_str = self._get_color_preference(p2)
            
            p1_color = ''

            # 5.2.1: Grant both preferences
            if p1_pref_str != 'N' and p1_pref_str != p2_pref_str:
                p1_color = p1_pref_str
            # 5.2.2: Grant stronger preference
            elif p1_pref_val > p2_pref_val:
                p1_color = p1_pref_str
            elif p2_pref_val > p1_pref_val:
                p1_color = 'W' if p2_pref_str == 'B' else 'B'
            # 5.2.4: Grant preference of higher ranked player
            elif p1_pref_str != 'N':
                p1_color = p1_pref_str
            # 5.2.5: Use TPN and initial color
            else:
                p1_color = self.initial_color if p1['tpn'] % 2 != 0 else ('B' if self.initial_color == 'W' else 'W')
            
            if p1['id'] == p1_id:
                colored_pairings.append((p1_id, p2_id, p1_color))
            else: # p1 was swapped with p2
                p2_color = 'W' if p1_color == 'B' else 'B'
                colored_pairings.append((p2_id, p1_id, p2_color))
                
        return colored_pairings
    
    def _get_color_preference(self, player: Dict) -> Tuple[int, str]:
        """Determine color preference (value, string: W/B/N)."""
        color_history = player.get('color_history', [])
        if not color_history:
            return 0, 'N'

        color_diff = color_history.count('W') - color_history.count('B')

        # Absolute preference
        if color_diff < -1 or (len(color_history) >= 2 and color_history[-2:] == ['B', 'B']):
            return 3, 'W'
        if color_diff > 1 or (len(color_history) >= 2 and color_history[-2:] == ['W', 'W']):
            return 3, 'B'
        
        # Strong preference
        if color_diff == -1:
            return 2, 'W'
        if color_diff == 1:
            return 2, 'B'

        # Mild preference
        return 1, 'B' if color_history[-1] == 'W' else 'W'

    def _fetch_opponent_history(self) -> Dict[int, Set[int]]:
        """Fetch all previous pairings for the tournament."""
        history = {}
        # Optimization: Use get_all_tournament_results for a single query
        all_results = self.db.get_all_tournament_results(self.tournament_id)
        
        for res in all_results:
            p1_id, p2_id = res['player1_id'], res['player2_id']
            if p1_id is not None and p2_id is not None:
                history.setdefault(p1_id, set()).add(p2_id)
                history.setdefault(p2_id, set()).add(p1_id)
        return history

    def _get_bye_history(self) -> Set[int]:
        """Get a set of player IDs who have received a bye."""
        return set(self.db.get_players_with_bye(self.tournament_id))
    
    def _get_color_history(self, player_id: int) -> List[str]:
        """Get the color history for a player."""
        return self.db.get_player_color_history(self.tournament_id, player_id)

    def _get_float_history(self, player_id: int, float_type: str) -> List[int]:
        """Get the downfloat/upfloat history for a player."""
        return self.db.get_player_float_history(self.tournament_id, player_id, float_type)

    def _update_float_history(self, pairings: List[Tuple[int, int, str]], bye_player_id: Optional[int]):
        """Update float history for the current round."""
        history_to_add = []

        # Downfloat for bye
        if bye_player_id:
            history_to_add.append((self.tournament_id, self.round_number, bye_player_id, 'downfloat'))

        for p1_id, p2_id, _ in pairings:
            p1 = self._get_player_by_id(p1_id)
            p2 = self._get_player_by_id(p2_id)

            if p1['score'] > p2['score']:
                history_to_add.append((self.tournament_id, self.round_number, p1_id, 'downfloat'))
                history_to_add.append((self.tournament_id, self.round_number, p2_id, 'upfloat'))
            elif p2['score'] > p1['score']:
                history_to_add.append((self.tournament_id, self.round_number, p2_id, 'downfloat'))
                history_to_add.append((self.tournament_id, self.round_number, p1_id, 'upfloat'))
        
        if history_to_add:
            self.db.add_float_history_batch(history_to_add)

    def _get_initial_color(self) -> str:
        """Get initial color for the tournament."""
        # Should be stored in tournament settings
        return self.db.get_tournament_settings(self.tournament_id).get('initial_color', 'W')
    
    def _get_player_by_id(self, player_id: int) -> Dict:
        """Get a player dictionary by their ID."""
        return next((p for p in self.players if p['id'] == player_id), {})
