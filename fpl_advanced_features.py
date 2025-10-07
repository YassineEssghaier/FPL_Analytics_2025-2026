"""
FPL Advanced Features - Game-Winning Analytics
Add these to your FPLPlayerAnalyzer class for competitive advantage
"""

import pandas as pd
import numpy as np
from fpl_data_fetcher import FPLDataFetcher

class FPLAdvancedAnalyzer:
    def __init__(self, analyzer):
        """Initialize with existing analyzer"""
        self.analyzer = analyzer
        self.fetcher = analyzer.fetcher
        
    def get_fixture_run_analysis(self, next_n_gameweeks=5):
        """
        Analyze which teams have the best fixture runs
        Returns teams sorted by easiest upcoming fixtures
        """
        fixtures_df = self.analyzer.fixtures_df
        players_df = self.analyzer.players_df
        
        # Get upcoming fixtures only
        upcoming = fixtures_df[fixtures_df['finished'] == False].copy()
        
        # Calculate average difficulty for each team
        team_fixtures = {}
        
        for team in players_df['team_short'].unique():
            team_games = upcoming[
                (upcoming['home_team'] == team) | (upcoming['away_team'] == team)
            ].head(next_n_gameweeks)
            
            if len(team_games) > 0:
                # Get FDR ratings
                home_fdr = team_games[team_games['home_team'] == team]['team_h_difficulty'].mean()
                away_fdr = team_games[team_games['away_team'] == team]['team_a_difficulty'].mean()
                avg_fdr = np.nanmean([home_fdr, away_fdr])
                
                # Count home games (home advantage)
                home_count = len(team_games[team_games['home_team'] == team])
                
                team_fixtures[team] = {
                    'team': team,
                    'avg_difficulty': avg_fdr if not np.isnan(avg_fdr) else 3,
                    'fixtures': len(team_games),
                    'home_games': home_count,
                    'away_games': len(team_games) - home_count
                }
        
        fixtures_analysis = pd.DataFrame(team_fixtures.values())
        fixtures_analysis = fixtures_analysis.sort_values('avg_difficulty')
        
        print(f"\n{'='*80}")
        print(f"BEST FIXTURE RUNS - NEXT {next_n_gameweeks} GAMEWEEKS")
        print(f"{'='*80}")
        print("Lower difficulty = Easier fixtures\n")
        print(fixtures_analysis.to_string(index=False))
        
        return fixtures_analysis
    
    def get_captaincy_picks(self, top_n=10):
        """
        Best captaincy options based on:
        - Form
        - Fixture difficulty
        - Home/Away
        - Historical ceiling
        """
        players_df = self.analyzer.players_df.copy()
        fixtures_df = self.analyzer.fixtures_df
        
        # Get next gameweek fixtures
        next_fixtures = fixtures_df[
            (fixtures_df['finished'] == False) & 
            (fixtures_df['event'] == fixtures_df[fixtures_df['finished'] == False]['event'].min())
        ]
        
        # Calculate captaincy score
        players_df['captaincy_score'] = (
            players_df['form'].astype(float) * 0.4 +
            players_df['points_per_game'].astype(float) * 0.3 +
            players_df['expected_goal_involvements'].astype(float) * 100 * 0.3
        )
        
        # Filter premium players (typically captain picks)
        captain_candidates = players_df[
            (players_df['price'] >= 8.0) & 
            (players_df['status'] == 'a') &
            (players_df['minutes'] > 450)
        ].copy()
        
        best_captains = captain_candidates.nlargest(top_n, 'captaincy_score')
        
        print(f"\n{'='*80}")
        print(f"TOP {top_n} CAPTAINCY PICKS THIS GAMEWEEK")
        print(f"{'='*80}")
        
        display_cols = ['web_name', 'team_short', 'position', 'price', 'form',
                       'points_per_game', 'expected_goals', 'expected_assists',
                       'captaincy_score', 'selected_by_percent']
        print(best_captains[display_cols].to_string(index=False))
        
        return best_captains
    
    def find_template_breakers(self, ownership_threshold=30.0, top_n=15):
        """
        Find players to avoid the template (highly owned players)
        These are alternatives to consider instead of popular picks
        """
        players_df = self.analyzer.players_df.copy()
        
        # Find template players (high ownership)
        template = players_df[
            players_df['selected_by_percent'].astype(float) >= ownership_threshold
        ].sort_values('selected_by_percent', ascending=False)
        
        print(f"\n{'='*80}")
        print(f"⚠️  TEMPLATE PLAYERS (>{ownership_threshold}% ownership)")
        print(f"{'='*80}")
        print("These are the players everyone has:\n")
        print(template[['web_name', 'team_short', 'position', 'price', 
                       'selected_by_percent', 'value_score']].head(10).to_string(index=False))
        
        # For each template player, find alternatives in same price range
        print(f"\n{'='*80}")
        print(f"💎 TEMPLATE BREAKERS - Alternative Picks")
        print(f"{'='*80}")
        
        breakers = []
        for _, template_player in template.head(5).iterrows():
            # Find alternatives ±0.5m
            alternatives = players_df[
                (players_df['position'] == template_player['position']) &
                (players_df['price'] >= template_player['price'] - 0.5) &
                (players_df['price'] <= template_player['price'] + 0.5) &
                (players_df['selected_by_percent'].astype(float) < ownership_threshold) &
                (players_df['status'] == 'a') &
                (players_df['id'] != template_player['id'])
            ].nlargest(2, 'value_score')
            
            if len(alternatives) > 0:
                print(f"\n🔄 Instead of {template_player['web_name']} ({template_player['selected_by_percent']}%):")
                print(alternatives[['web_name', 'team_short', 'price', 
                                   'form', 'selected_by_percent', 'value_score']].to_string(index=False))
                breakers.extend(alternatives.to_dict('records'))
        
        return pd.DataFrame(breakers)
    
    def points_prediction_next_gw(self, player_id):
        """
        Predict points for next gameweek using simple model
        Based on: form, fixture difficulty, home/away, xG/xA
        """
        players_df = self.analyzer.players_df
        player = players_df[players_df['id'] == player_id].iloc[0]
        
        # Base prediction on recent form
        base_points = float(player['form']) if player['form'] else 2.0
        
        # Adjust for fixture difficulty (placeholder - needs fixture data)
        fixture_multiplier = 1.0  # Would check next opponent
        
        # Adjust for expected goals/assists
        xg_boost = float(player['expected_goals']) * 0.5 if player['expected_goals'] else 0
        xa_boost = float(player['expected_assists']) * 0.3 if player['expected_assists'] else 0
        
        predicted = (base_points * fixture_multiplier) + xg_boost + xa_boost
        
        return round(predicted, 1)
    
    def mini_league_strategy(self, my_team_ids, rival_team_ids):
        """
        Compare your team vs rival's team
        Identify where you have advantage/disadvantage
        """
        players_df = self.analyzer.players_df
        
        my_team = players_df[players_df['id'].isin(my_team_ids)]
        rival_team = players_df[players_df['id'].isin(rival_team_ids)]
        
        # Find differential picks (players you have that rival doesn't)
        my_differentials = my_team[~my_team['id'].isin(rival_team_ids)]
        rival_differentials = rival_team[~rival_team['id'].isin(my_team_ids)]
        
        print(f"\n{'='*80}")
        print(f"⚔️  MINI-LEAGUE HEAD-TO-HEAD ANALYSIS")
        print(f"{'='*80}")
        
        print(f"\nYour Team Value Score: {my_team['value_score'].mean():.3f}")
        print(f"Rival Team Value Score: {rival_team['value_score'].mean():.3f}")
        
        print(f"\n{'='*80}")
        print(f"🎯 YOUR DIFFERENTIAL PICKS (Players rival doesn't have)")
        print(f"{'='*80}")
        if len(my_differentials) > 0:
            print(my_differentials[['web_name', 'team_short', 'position', 
                                    'form', 'value_score']].to_string(index=False))
        else:
            print("No differentials - you have the same players!")
        
        print(f"\n{'='*80}")
        print(f"⚠️  RIVAL'S DIFFERENTIAL PICKS (Players you don't have)")
        print(f"{'='*80}")
        if len(rival_differentials) > 0:
            print(rival_differentials[['web_name', 'team_short', 'position', 
                                      'form', 'value_score']].to_string(index=False))
        else:
            print("Rival has no differentials!")
        
        # Identify risky rival picks you should consider covering
        high_threat = rival_differentials[
            (rival_differentials['form'].astype(float) > 6.0) |
            (rival_differentials['value_score'] > 0.7)
        ]
        
        if len(high_threat) > 0:
            print(f"\n{'='*80}")
            print(f"🚨 HIGH THREAT: Consider covering these rival picks")
            print(f"{'='*80}")
            print(high_threat[['web_name', 'team_short', 'form', 'value_score']].to_string(index=False))
        
        return {
            'my_differentials': my_differentials,
            'rival_differentials': rival_differentials,
            'high_threat': high_threat if len(high_threat) > 0 else None
        }
    
    def wildcard_optimizer(self, budget=100.0, must_have_ids=None):
        """
        Build optimal team for Wildcard chip
        Focuses on fixture runs, form, and value
        """
        players_df = self.analyzer.players_df.copy()
        
        print(f"\n{'='*80}")
        print(f"🃏 WILDCARD TEAM OPTIMIZER")
        print(f"{'='*80}")
        print(f"Budget: £{budget}m")
        
        # Get best fixture runs
        fixture_analysis = self.get_fixture_run_analysis(next_n_gameweeks=8)
        good_fixture_teams = fixture_analysis.head(8)['team'].tolist()
        
        # Boost value score for players from teams with good fixtures
        players_df['wildcard_score'] = players_df['value_score'].copy()
        players_df.loc[
            players_df['team_short'].isin(good_fixture_teams), 
            'wildcard_score'
        ] *= 1.2
        
        squad = []
        remaining_budget = budget
        must_have = must_have_ids if must_have_ids else []
        
        formation = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
        
        # First add must-have players
        if must_have:
            must_have_players = players_df[players_df['id'].isin(must_have)]
            for _, player in must_have_players.iterrows():
                squad.append(player)
                remaining_budget -= player['price']
                formation[player['position']] -= 1
        
        # Fill remaining positions
        for position, count in formation.items():
            if count <= 0:
                continue
                
            position_players = players_df[
                (players_df['position'] == position) &
                (players_df['status'] == 'a') &
                (~players_df['id'].isin([p['id'] for p in squad]))
            ].sort_values('wildcard_score', ascending=False)
            
            selected = 0
            for _, player in position_players.iterrows():
                if selected >= count:
                    break
                if player['price'] <= remaining_budget:
                    squad.append(player)
                    remaining_budget -= player['price']
                    selected += 1
        
        squad_df = pd.DataFrame(squad)
        
        print(f"\nTotal Cost: £{squad_df['price'].sum():.1f}m")
        print(f"Remaining: £{remaining_budget:.1f}m")
        print(f"Avg Value Score: {squad_df['wildcard_score'].mean():.3f}")
        print(f"\n{'-'*80}\n")
        print(squad_df[['web_name', 'team_short', 'position', 'price', 
                       'form', 'wildcard_score']].to_string(index=False))
        
        return squad_df
    
    def bench_boost_analyzer(self):
        """
        Identify best gameweek to use Bench Boost
        Based on: fixtures, DGWs, team depth
        """
        print(f"\n{'='*80}")
        print(f"📊 BENCH BOOST OPTIMIZER")
        print(f"{'='*80}")
        
        # Get fixture analysis for next 10 gameweeks
        fixture_analysis = self.get_fixture_run_analysis(next_n_gameweeks=10)
        
        print("\nBest Gameweeks for Bench Boost:")
        print("1. Look for Double Gameweeks (check FPL website)")
        print("2. Gameweeks where your bench players have good fixtures")
        print("3. When your expensive bench players are likely to start")
        
        print(f"\nTeams with easiest fixtures (target for bench):")
        print(fixture_analysis.head(5)[['team', 'avg_difficulty', 'home_games']].to_string(index=False))
        
        return fixture_analysis


# Integration example - add to your FPLAssistant class
def add_advanced_features_to_assistant(assistant):
    """
    Add advanced features to existing FPLAssistant
    Call this after initializing your assistant
    """
    assistant.advanced = FPLAdvancedAnalyzer(assistant.analyzer)
    
    # Add convenience methods
    def get_captaincy_picks(top_n=10):
        return assistant.advanced.get_captaincy_picks(top_n)
    
    def get_fixture_analysis(next_n=5):
        return assistant.advanced.get_fixture_run_analysis(next_n)
    
    def find_template_breakers(ownership=30.0):
        return assistant.advanced.find_template_breakers(ownership)
    
    def compare_vs_rival(my_team_ids, rival_team_ids):
        return assistant.advanced.mini_league_strategy(my_team_ids, rival_team_ids)
    
    def plan_wildcard(budget=100.0, must_have=None):
        return assistant.advanced.wildcard_optimizer(budget, must_have)
    
    def plan_bench_boost():
        return assistant.advanced.bench_boost_analyzer()
    
    # Attach methods
    assistant.get_captaincy_picks = get_captaincy_picks
    assistant.get_fixture_analysis = get_fixture_analysis
    assistant.find_template_breakers = find_template_breakers
    assistant.compare_vs_rival = compare_vs_rival
    assistant.plan_wildcard = plan_wildcard
    assistant.plan_bench_boost = plan_bench_boost
    
    print("\n✅ Advanced features loaded!")
    print("\nNew commands available:")
    print("  - assistant.get_captaincy_picks()")
    print("  - assistant.get_fixture_analysis()")
    print("  - assistant.find_template_breakers()")
    print("  - assistant.compare_vs_rival(my_ids, rival_ids)")
    print("  - assistant.plan_wildcard()")
    print("  - assistant.plan_bench_boost()")


# Example usage
if __name__ == "__main__":
    from fpl_main_app import FPLAssistant
    
    assistant = FPLAssistant()
    assistant.initialize()
    
    # Add advanced features
    add_advanced_features_to_assistant(assistant)
    
    # Use advanced features
    assistant.get_captaincy_picks(top_n=10)
    assistant.get_fixture_analysis(next_n=5)
    assistant.find_template_breakers(ownership=30.0)