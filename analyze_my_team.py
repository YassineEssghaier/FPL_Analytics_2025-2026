"""
FPL Player Analyzer - Analyzes players and recommends best picks
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from fpl_data_fetcher import FPLDataFetcher

class FPLPlayerAnalyzer:
    def __init__(self):
        self.fetcher = FPLDataFetcher()
        self.players_df = None
        self.fixtures_df = None
        self.scaler = MinMaxScaler()
        
    def load_data(self):
        """Load all necessary data"""
        print("Loading FPL data...")
        self.players_df = self.fetcher.get_all_players_df()
        self.fixtures_df = self.fetcher.get_fixtures_df()
        print(f"Loaded {len(self.players_df)} players")
        
    def calculate_value_score(self):
        """Calculate value score for each player"""
        df = self.players_df.copy()
        
        # Filter out players with no minutes
        df = df[df['minutes'] > 0].copy()
        
        # Convert string percentages to float
        df['selected_by_percent'] = pd.to_numeric(df['selected_by_percent'], errors='coerce')
        df['form'] = pd.to_numeric(df['form'], errors='coerce')
        df['points_per_game'] = pd.to_numeric(df['points_per_game'], errors='coerce')
        df['ict_index'] = pd.to_numeric(df['ict_index'], errors='coerce')
        df['expected_goals'] = pd.to_numeric(df['expected_goals'], errors='coerce')
        df['expected_assists'] = pd.to_numeric(df['expected_assists'], errors='coerce')
        
        # Fill NaN values
        df.fillna(0, inplace=True)
        
        # Calculate points per million
        df['points_per_million'] = df['total_points'] / df['price']
        df['form_per_million'] = df['form'].astype(float) / df['price']
        
        # Calculate expected involvement
        df['expected_involvement'] = df['expected_goals'] + df['expected_assists']
        
        # Normalize key metrics
        metrics = ['points_per_game', 'form', 'points_per_million', 'ict_index', 'expected_involvement']
        
        for metric in metrics:
            if metric in df.columns:
                df[f'{metric}_normalized'] = self.scaler.fit_transform(df[[metric]])
        
        # Calculate composite value score (weighted average)
        weights = {
            'points_per_game_normalized': 0.25,
            'form_normalized': 0.25,
            'points_per_million_normalized': 0.20,
            'ict_index_normalized': 0.15,
            'expected_involvement_normalized': 0.15
        }
        
        df['value_score'] = sum(df[col] * weight for col, weight in weights.items())
        
        # Penalize for injury/availability
        df.loc[df['chance_of_playing_next_round'] < 100, 'value_score'] *= 0.5
        df.loc[df['status'] != 'a', 'value_score'] *= 0.3
        
        self.players_df = df
        return df
    
    def get_fixture_difficulty(self, team_name, next_n_games=5):
        """Calculate fixture difficulty for a team over next N games"""
        upcoming = self.fixtures_df[
            (self.fixtures_df['finished'] == False) &
            ((self.fixtures_df['home_team'] == team_name) | 
             (self.fixtures_df['away_team'] == team_name))
        ].head(next_n_games)
        
        if len(upcoming) == 0:
            return 3  # neutral difficulty
        
        # Average FDR (Fixture Difficulty Rating)
        home_fdr = upcoming[upcoming['home_team'] == team_name]['team_h_difficulty'].mean()
        away_fdr = upcoming[upcoming['away_team'] == team_name]['team_a_difficulty'].mean()
        
        avg_fdr = np.nanmean([home_fdr, away_fdr])
        return avg_fdr if not np.isnan(avg_fdr) else 3
    
    def recommend_best_players(self, position=None, top_n=10):
        """Recommend best players overall or by position"""
        if self.players_df is None or 'value_score' not in self.players_df.columns:
            self.calculate_value_score()
        
        df = self.players_df.copy()
        
        if position:
            df = df[df['position'] == position]
        
        # Sort by value score
        best_players = df.nlargest(top_n, 'value_score')
        
        # Select relevant columns for display
        display_cols = [
            'web_name', 'team_short', 'position', 'price', 'total_points',
            'points_per_game', 'form', 'points_per_million', 'selected_by_percent',
            'value_score', 'status', 'news'
        ]
        
        return best_players[display_cols]
    
    def build_optimal_squad(self, budget=100.0):
        """
        Build optimal 15-player squad within budget
        Formation: 2 GK, 5 DEF, 5 MID, 3 FWD
        Respects 3 players per team rule
        """
        if self.players_df is None or 'value_score' not in self.players_df.columns:
            self.calculate_value_score()
        
        squad = []
        remaining_budget = budget
        team_counts = {}  # Track players per team
        
        formation = {
            'GK': 2,
            'DEF': 5,
            'MID': 5,
            'FWD': 3
        }
        
        for position, count in formation.items():
            position_players = self.players_df[
                (self.players_df['position'] == position) &
                (self.players_df['status'] == 'a')
            ].copy()
            
            # Sort by value score
            position_players = position_players.sort_values('value_score', ascending=False)
            
            selected = 0
            for _, player in position_players.iterrows():
                if selected >= count:
                    break
                
                player_team = player['team_short']
                current_team_count = team_counts.get(player_team, 0)
                
                # Check if adding this player violates 3-per-team rule
                if current_team_count >= 3:
                    continue  # Skip this player
                
                if player['price'] <= remaining_budget:
                    squad.append(player)
                    remaining_budget -= player['price']
                    team_counts[player_team] = current_team_count + 1
                    selected += 1
        
        squad_df = pd.DataFrame(squad)
        total_cost = squad_df['price'].sum()
        
        print(f"\n{'='*80}")
        print(f"OPTIMAL 15-PLAYER SQUAD (Budget: £{budget}m)")
        print(f"{'='*80}")
        print(f"Total Cost: £{total_cost:.1f}m | Remaining: £{budget - total_cost:.1f}m")
        
        # Show team composition
        print(f"\n{'='*80}")
        print(f"TEAM COMPOSITION (Max 3 per team)")
        print(f"{'='*80}")
        for team, count in sorted(team_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {team}: {count} player(s)")
        
        print(f"\nSquad:\n")
        print(squad_df[['web_name', 'team_short', 'position', 'price', 'total_points', 'form', 'value_score']].to_string(index=False))
        
        return squad_df
    
    def recommend_transfers(self, current_team_ids, transfers_available=1):
        """
        Recommend best transfers based on current team
        Returns top 3 recommendations per position
        """
        if self.players_df is None or 'value_score' not in self.players_df.columns:
            self.calculate_value_score()
        
        # Get current team
        current_team = self.players_df[self.players_df['id'].isin(current_team_ids)].copy()
        
        # Count players per team in current squad
        team_counts = current_team['team_short'].value_counts().to_dict()
        
        # Get available players (not in current team)
        available = self.players_df[~self.players_df['id'].isin(current_team_ids)].copy()
        
        all_recommendations = []
        
        for position in ['GK', 'DEF', 'MID', 'FWD']:
            current_pos = current_team[current_team['position'] == position]
            available_pos = available[available['position'] == position]
            
            print(f"\n{'='*80}")
            print(f"📊 {position} TRANSFER RECOMMENDATIONS (Top 3)")
            print(f"{'='*80}")
            
            position_recommendations = []
            
            for _, current_player in current_pos.iterrows():
                # Find better replacements within ±1.5m price range
                price_min = current_player['price'] - 1.5
                price_max = current_player['price'] + 1.5
                
                replacements = available_pos[
                    (available_pos['price'] >= price_min) &
                    (available_pos['price'] <= price_max) &
                    (available_pos['value_score'] > current_player['value_score']) &
                    (available_pos['status'] == 'a')
                ].nlargest(100, 'value_score')  # Get more candidates
                
                for _, replacement in replacements.iterrows():
                    # CHECK: 3 players per team rule
                    replacement_team = replacement['team_short']
                    current_player_team = current_player['team_short']
                    
                    if replacement_team in team_counts:
                        if replacement_team == current_player_team:
                            team_count_after = team_counts[replacement_team]
                        else:
                            if team_counts[replacement_team] >= 3:
                                continue
                            team_count_after = team_counts[replacement_team] + 1
                    else:
                        team_count_after = 1
                    
                    if team_count_after <= 3:
                        score_improvement = replacement['value_score'] - current_player['value_score']
                        position_recommendations.append({
                            'position': position,
                            'out': current_player['web_name'],
                            'out_team': current_player['team_short'],
                            'out_price': current_player['price'],
                            'out_score': current_player['value_score'],
                            'out_form': current_player['form'],
                            'in': replacement['web_name'],
                            'in_team': replacement['team_short'],
                            'in_price': replacement['price'],
                            'in_score': replacement['value_score'],
                            'in_form': replacement['form'],
                            'price_change': replacement['price'] - current_player['price'],
                            'score_improvement': score_improvement,
                            'team_count_after': team_count_after
                        })
            
            # Get top 3 for this position
            position_recommendations = sorted(
                position_recommendations, 
                key=lambda x: x['score_improvement'], 
                reverse=True
            )[:3]
            
            if position_recommendations:
                # Display top 3 for this position
                for i, rec in enumerate(position_recommendations, 1):
                    print(f"\n{position} Option {i}:")
                    print(f"  OUT: {rec['out']} ({rec['out_team']}) - £{rec['out_price']}m | Form: {rec['out_form']}")
                    print(f"  IN:  {rec['in']} ({rec['in_team']}) - £{rec['in_price']}m | Form: {rec['in_form']}")
                    print(f"  💰 Price: £{rec['price_change']:+.1f}m | 📈 Value: +{rec['score_improvement']:.3f}")
                
                all_recommendations.extend(position_recommendations)
            else:
                print(f"  ✅ No better {position} options available")
        
        # Show current team composition
        print(f"\n{'='*80}")
        print(f"YOUR CURRENT TEAM COMPOSITION")
        print(f"{'='*80}")
        for team, count in sorted(team_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {team}: {count} player(s)")
        
        # Overall best recommendations
        if all_recommendations:
            print(f"\n{'='*80}")
            print(f"🎯 OVERALL TOP RECOMMENDATIONS (All Positions)")
            print(f"{'='*80}\n")
            
            # Sort all by score improvement
            top_overall = sorted(all_recommendations, key=lambda x: x['score_improvement'], reverse=True)[:transfers_available * 3]
            
            recommendations_df = pd.DataFrame(top_overall)
            display_df = recommendations_df.drop('team_count_after', axis=1)
            print(display_df.to_string(index=False))
            
            return recommendations_df
        else:
            print("\n✅ Your team is already optimized! No better transfers available.")
            return pd.DataFrame()


# Example usage
if __name__ == "__main__":
    analyzer = FPLPlayerAnalyzer()
    analyzer.load_data()
    
    # Calculate value scores
    analyzer.calculate_value_score()
    
    print("\n" + "="*80)
    print("TOP 10 BEST VALUE PLAYERS OVERALL")
    print("="*80)
    print(analyzer.recommend_best_players(top_n=10))
    
    print("\n" + "="*80)
    print("TOP 10 BEST VALUE MIDFIELDERS")
    print("="*80)
    print(analyzer.recommend_best_players(position='MID', top_n=10))
    
    # Build optimal squad
    squad = analyzer.build_optimal_squad(budget=100.0)
    
    # Example: Recommend transfers (replace these IDs with your actual team)
    # current_team_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    # analyzer.recommend_transfers(current_team_ids, transfers_available=1)