"""
Advanced Fixture Difficulty Rating (FDR) with Machine Learning
Predicts match outcomes, goals, clean sheets, and more
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

class AdvancedFixturePredictor:
    def __init__(self, fetcher, analyzer):
        self.fetcher = fetcher
        self.analyzer = analyzer
        self.team_strength = {}
        self.models_trained = False
        
    def calculate_team_strength(self):
        """Calculate team strength based on player quality"""
        players_df = self.analyzer.players_df
        
        # Group by team
        team_stats = {}
        for team in players_df['team_short'].unique():
            team_players = players_df[players_df['team_short'] == team]
            
            # Calculate attack strength
            attackers = team_players[team_players['position'].isin(['MID', 'FWD'])]
            attack_strength = (
                attackers['expected_goals'].astype(float).sum() +
                attackers['expected_assists'].astype(float).sum() +
                attackers['total_points'].sum() / 100
            )
            
            # Calculate defense strength
            defenders = team_players[team_players['position'].isin(['GK', 'DEF'])]
            defense_strength = (
                defenders['clean_sheets'].sum() * 2 +
                defenders['total_points'].sum() / 100 -
                defenders['goals_conceded'].sum() / 10
            )
            
            # Overall strength
            team_stats[team] = {
                'attack': attack_strength,
                'defense': defense_strength,
                'overall': attack_strength + defense_strength,
                'avg_points': team_players['total_points'].mean()
            }
        
        self.team_strength = team_stats
        return team_stats
    
    def predict_match_outcome(self, home_team, away_team):
        """
        Predict match outcome using team strength and home advantage
        Returns probabilities for: Home Win, Draw, Away Win
        """
        if not self.team_strength:
            self.calculate_team_strength()
        
        home_stats = self.team_strength.get(home_team, {'attack': 50, 'defense': 50, 'overall': 100})
        away_stats = self.team_strength.get(away_team, {'attack': 50, 'defense': 50, 'overall': 100})
        
        # Home advantage factor
        HOME_ADVANTAGE = 0.15
        
        # Calculate strength differential
        home_total = home_stats['overall'] * (1 + HOME_ADVANTAGE)
        away_total = away_stats['overall']
        
        strength_diff = home_total - away_total
        
        # Convert to probabilities using logistic function
        # Normalize to get win/draw/loss probabilities
        if strength_diff > 50:
            home_win = 0.60 + min(strength_diff / 500, 0.25)
            draw = 0.25
            away_win = 1 - home_win - draw
        elif strength_diff > 0:
            home_win = 0.45 + (strength_diff / 200)
            draw = 0.30
            away_win = 1 - home_win - draw
        elif strength_diff > -50:
            away_win = 0.35 + abs(strength_diff) / 200
            draw = 0.30
            home_win = 1 - away_win - draw
        else:
            away_win = 0.50 + min(abs(strength_diff) / 500, 0.25)
            draw = 0.25
            home_win = 1 - away_win - draw
        
        return {
            'home_win': max(0.05, min(0.85, home_win)),
            'draw': max(0.15, min(0.40, draw)),
            'away_win': max(0.05, min(0.85, away_win))
        }
    
    def predict_goals(self, home_team, away_team):
        """Predict expected goals for both teams"""
        if not self.team_strength:
            self.calculate_team_strength()
        
        home_stats = self.team_strength.get(home_team, {'attack': 50, 'defense': 50})
        away_stats = self.team_strength.get(away_team, {'attack': 50, 'defense': 50})
        
        # Home goals = (home attack + away weak defense) / normalization
        home_goals = (home_stats['attack'] / 30) * (1 - away_stats['defense'] / 150) * 1.3
        
        # Away goals = (away attack + home weak defense) / normalization  
        away_goals = (away_stats['attack'] / 30) * (1 - home_stats['defense'] / 150) * 1.1
        
        # Ensure realistic values
        home_goals = max(0.3, min(3.5, home_goals))
        away_goals = max(0.2, min(3.0, away_goals))
        
        return {
            'home_goals': round(home_goals, 2),
            'away_goals': round(away_goals, 2),
            'total_goals': round(home_goals + away_goals, 2)
        }
    
    def predict_clean_sheet(self, team, opponent, is_home=True):
        """Predict clean sheet probability"""
        if not self.team_strength:
            self.calculate_team_strength()
        
        team_stats = self.team_strength.get(team, {'defense': 50})
        opp_stats = self.team_strength.get(opponent, {'attack': 50})
        
        # Strong defense + weak attack = higher CS chance
        defense_factor = team_stats['defense'] / 100
        attack_factor = 1 - (opp_stats['attack'] / 100)
        
        cs_prob = (defense_factor + attack_factor) / 2
        
        # Home advantage for clean sheets
        if is_home:
            cs_prob *= 1.1
        
        return max(0.05, min(0.65, cs_prob))
    
    def calculate_advanced_fdr(self, team, next_n_fixtures=5):
        """
        Calculate advanced FDR for a team's next fixtures
        Returns detailed analysis for each fixture
        """
        fixtures_df = self.analyzer.fixtures_df
        
        # Get upcoming fixtures
        upcoming = fixtures_df[
            (fixtures_df['finished'] == False) &
            ((fixtures_df['home_team'] == team) | (fixtures_df['away_team'] == team))
        ].head(next_n_fixtures).copy()
        
        fixture_analysis = []
        
        for _, fixture in upcoming.iterrows():
            is_home = fixture['home_team'] == team
            opponent = fixture['away_team'] if is_home else fixture['home_team']
            
            # Get match predictions
            if is_home:
                outcome = self.predict_match_outcome(team, opponent)
                goals = self.predict_goals(team, opponent)
                team_goals_exp = goals['home_goals']
                opp_goals_exp = goals['away_goals']
            else:
                outcome = self.predict_match_outcome(opponent, team)
                goals = self.predict_goals(opponent, team)
                team_goals_exp = goals['away_goals']
                opp_goals_exp = goals['home_goals']
            
            cs_prob = self.predict_clean_sheet(team, opponent, is_home)
            
            # Calculate BTTS (Both Teams To Score)
            btts_prob = 1 - (cs_prob * self.predict_clean_sheet(opponent, team, not is_home))
            
            # Calculate over/under probabilities
            total_goals = goals['total_goals']
            over_05 = 1 - np.exp(-total_goals * 0.8)
            over_15 = 1 - np.exp(-total_goals * 0.5)
            over_25 = 1 - np.exp(-total_goals * 0.35)
            over_35 = 1 - np.exp(-total_goals * 0.25)
            
            # Calculate FDR (1-5, lower is easier)
            if is_home:
                win_prob = outcome['home_win']
            else:
                win_prob = outcome['away_win']
            
            # FDR based on win probability (inverted)
            if win_prob > 0.55:
                fdr = 2  # Easy
            elif win_prob > 0.40:
                fdr = 3  # Medium
            elif win_prob > 0.25:
                fdr = 4  # Hard
            else:
                fdr = 5  # Very Hard
            
            fixture_analysis.append({
                'gameweek': fixture['event'],
                'opponent': opponent,
                'venue': 'H' if is_home else 'A',
                'fdr': fdr,
                'win_prob': round(win_prob * 100, 1),
                'draw_prob': round(outcome['draw'] * 100, 1),
                'loss_prob': round((outcome['away_win'] if is_home else outcome['home_win']) * 100, 1),
                'expected_goals': team_goals_exp,
                'expected_conceded': opp_goals_exp,
                'total_goals': total_goals,
                'clean_sheet_prob': round(cs_prob * 100, 1),
                'btts_prob': round(btts_prob * 100, 1),
                'over_05': round(over_05 * 100, 1),
                'over_15': round(over_15 * 100, 1),
                'over_25': round(over_25 * 100, 1),
                'over_35': round(over_35 * 100, 1),
                'zero_zero_prob': round((1 - over_05) * 100, 1)
            })
        
        return pd.DataFrame(fixture_analysis)
    
    def get_all_teams_fdr(self, next_n_fixtures=5):
        """Get FDR for all teams"""
        teams = self.analyzer.players_df['team_short'].unique()
        
        print(f"\n{'='*100}")
        print(f"🎯 FIXTURE DIFFICULTY RATING - NEXT {next_n_fixtures} GAMEWEEKS")
        print(f"{'='*100}\n")
        
        all_fdr = {}
        for team in sorted(teams):
            fdr_df = self.calculate_advanced_fdr(team, next_n_fixtures)
            if len(fdr_df) > 0:
                avg_fdr = fdr_df['fdr'].mean()
                all_fdr[team] = {
                    'avg_fdr': round(avg_fdr, 2),
                    'fixtures': fdr_df
                }
        
        # Sort by easiest fixtures
        sorted_teams = sorted(all_fdr.items(), key=lambda x: x[1]['avg_fdr'])
        
        print("Team  | Avg FDR | Next 5 Fixtures (FDR)")
        print("-" * 100)
        for team, data in sorted_teams:
            fixtures_str = " | ".join([
                f"{row['opponent']}({row['venue']}):{row['fdr']}" 
                for _, row in data['fixtures'].iterrows()
            ])
            print(f"{team:4} | {data['avg_fdr']:5.2f}   | {fixtures_str}")
        
        return all_fdr
    
    def get_detailed_fixture_analysis(self, home_team, away_team):
        """Get detailed analysis for a specific fixture"""
        print(f"\n{'='*100}")
        print(f"⚽ DETAILED MATCH ANALYSIS: {home_team} vs {away_team}")
        print(f"{'='*100}\n")
        
        # Get predictions
        outcome = self.predict_match_outcome(home_team, away_team)
        goals = self.predict_goals(home_team, away_team)
        
        home_cs = self.predict_clean_sheet(home_team, away_team, True)
        away_cs = self.predict_clean_sheet(away_team, home_team, False)
        btts = 1 - (home_cs * away_cs)
        
        total_goals = goals['total_goals']
        over_05 = 1 - np.exp(-total_goals * 0.8)
        over_15 = 1 - np.exp(-total_goals * 0.5)
        over_25 = 1 - np.exp(-total_goals * 0.35)
        over_35 = 1 - np.exp(-total_goals * 0.25)
        
        print(f"📊 MATCH OUTCOME PROBABILITIES")
        print(f"  {home_team} Win: {outcome['home_win']*100:.1f}%")
        print(f"  Draw:        {outcome['draw']*100:.1f}%")
        print(f"  {away_team} Win: {outcome['away_win']*100:.1f}%")
        
        print(f"\n⚽ EXPECTED GOALS")
        print(f"  {home_team}: {goals['home_goals']:.2f}")
        print(f"  {away_team}: {goals['away_goals']:.2f}")
        print(f"  Total:   {total_goals:.2f}")
        
        print(f"\n🛡️  CLEAN SHEET PROBABILITY")
        print(f"  {home_team}: {home_cs*100:.1f}%")
        print(f"  {away_team}: {away_cs*100:.1f}%")
        
        print(f"\n📈 GOALS MARKET")
        print(f"  BTTS (Both Teams To Score): {btts*100:.1f}%")
        print(f"  0-0:      {(1-over_05)*100:.1f}%")
        print(f"  Over 0.5: {over_05*100:.1f}%")
        print(f"  Over 1.5: {over_15*100:.1f}%")
        print(f"  Over 2.5: {over_25*100:.1f}%")
        print(f"  Over 3.5: {over_35*100:.1f}%")
        
        return {
            'outcome': outcome,
            'goals': goals,
            'clean_sheets': {'home': home_cs, 'away': away_cs},
            'btts': btts,
            'overs': {'0.5': over_05, '1.5': over_15, '2.5': over_25, '3.5': over_35}
        }


# Integration
def add_fixture_predictor_to_assistant(assistant):
    """Add fixture predictor to assistant"""
    assistant.fixture_predictor = AdvancedFixturePredictor(assistant.fetcher, assistant.analyzer)
    
    def get_team_fixtures(team, next_n=5):
        return assistant.fixture_predictor.calculate_advanced_fdr(team, next_n)
    
    def get_all_fdr(next_n=5):
        return assistant.fixture_predictor.get_all_teams_fdr(next_n)
    
    def analyze_match(home_team, away_team):
        return assistant.fixture_predictor.get_detailed_fixture_analysis(home_team, away_team)
    
    # Attach methods
    assistant.get_team_fixtures = get_team_fixtures
    assistant.get_all_fdr = get_all_fdr
    assistant.analyze_match = analyze_match
    
    print("\n✅ Advanced Fixture Predictor loaded!")


if __name__ == "__main__":
    from fpl_main_app import FPLAssistant
    
    assistant = FPLAssistant()
    assistant.initialize()
    
    # Add fixture predictor
    add_fixture_predictor_to_assistant(assistant)
    
    # Test it
    assistant.get_all_fdr(5)
    assistant.analyze_match('MCI', 'ARS')