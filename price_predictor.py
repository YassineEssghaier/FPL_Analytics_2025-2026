"""
FPL Price Change Predictor
Predicts which players will rise/drop in price
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class PriceChangePredictor:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.threshold_rise = 100  # Net transfers needed for price rise
        self.threshold_drop = -100  # Net transfers needed for price drop
        
    def get_price_change_predictions(self):
        """
        Predict price changes based on ownership trends
        Returns players likely to rise/drop tonight
        """
        # Get current data
        data = self.fetcher.fetch_bootstrap_data()
        players_df = pd.DataFrame(data['elements'])
        teams_df = pd.DataFrame(data['teams'])
        
        # Add team names
        team_map = dict(zip(teams_df['id'], teams_df['short_name']))
        players_df['team_short'] = players_df['team'].map(team_map)
        
        # Calculate price change likelihood
        players_df['selected_by_percent'] = pd.to_numeric(players_df['selected_by_percent'], errors='coerce')
        players_df['transfers_in_event'] = pd.to_numeric(players_df['transfers_in_event'], errors='coerce')
        players_df['transfers_out_event'] = pd.to_numeric(players_df['transfers_out_event'], errors='coerce')
        
        # Net transfers
        players_df['net_transfers'] = players_df['transfers_in_event'] - players_df['transfers_out_event']
        
        # Estimate transfer index (simplified FPL algorithm)
        players_df['transfer_index'] = (players_df['net_transfers'] / 
                                        (players_df['selected_by_percent'] * 1000 + 1))
        
        # Price change probability
        players_df['rise_probability'] = np.where(
            players_df['transfer_index'] > 0.005, 
            np.minimum(players_df['transfer_index'] * 100, 100), 
            0
        )
        
        players_df['drop_probability'] = np.where(
            players_df['transfer_index'] < -0.005,
            np.minimum(abs(players_df['transfer_index']) * 100, 100),
            0
        )
        
        # Position names
        position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        players_df['position'] = players_df['element_type'].map(position_map)
        
        # Price in millions
        players_df['price'] = players_df['now_cost'] / 10
        
        return players_df
    
    def get_rising_players(self, top_n=20):
        """Get players most likely to rise in price"""
        df = self.get_price_change_predictions()
        
        risers = df[
            (df['rise_probability'] > 30) &
            (df['status'] == 'a')
        ].nlargest(top_n, 'rise_probability')
        
        result = risers[[
            'web_name', 'team_short', 'position', 'price', 
            'selected_by_percent', 'net_transfers', 'rise_probability'
        ]].copy()
        
        result['prediction'] = 'RISING TONIGHT ⬆️'
        
        print(f"\n{'='*80}")
        print(f"💰 PLAYERS LIKELY TO RISE IN PRICE (Top {top_n})")
        print(f"{'='*80}")
        print(result.to_string(index=False))
        
        return result
    
    def get_dropping_players(self, top_n=20):
        """Get players most likely to drop in price"""
        df = self.get_price_change_predictions()
        
        fallers = df[
            (df['drop_probability'] > 30) &
            (df['status'] == 'a')
        ].nlargest(top_n, 'drop_probability')
        
        result = fallers[[
            'web_name', 'team_short', 'position', 'price',
            'selected_by_percent', 'net_transfers', 'drop_probability'
        ]].copy()
        
        result['prediction'] = 'DROPPING TONIGHT ⬇️'
        
        print(f"\n{'='*80}")
        print(f"📉 PLAYERS LIKELY TO DROP IN PRICE (Top {top_n})")
        print(f"{'='*80}")
        print(result.to_string(index=False))
        
        return result
    
    def check_my_team_prices(self, player_ids):
        """Check if any players in your team will change price"""
        df = self.get_price_change_predictions()
        
        my_team = df[df['id'].isin(player_ids)].copy()
        
        # Check for price changes
        rising = my_team[my_team['rise_probability'] > 50]
        dropping = my_team[my_team['drop_probability'] > 50]
        
        print(f"\n{'='*80}")
        print(f"🔔 YOUR TEAM PRICE CHANGE ALERTS")
        print(f"{'='*80}")
        
        if len(rising) > 0:
            print(f"\n✅ RISING SOON (Lock in value!):")
            print(rising[['web_name', 'team_short', 'price', 'rise_probability']].to_string(index=False))
        
        if len(dropping) > 0:
            print(f"\n⚠️  DROPPING SOON (Consider selling!):")
            print(dropping[['web_name', 'team_short', 'price', 'drop_probability']].to_string(index=False))
        
        if len(rising) == 0 and len(dropping) == 0:
            print("\n✅ No significant price changes expected in your team!")
        
        return {'rising': rising, 'dropping': dropping}
    
    def get_best_buys_before_rise(self, top_n=15):
        """Find best value players about to rise in price"""
        df = self.get_price_change_predictions()
        
        # Calculate value score (simplified)
        df['form'] = pd.to_numeric(df['form'], errors='coerce')
        df['points_per_game'] = pd.to_numeric(df['points_per_game'], errors='coerce')
        
        df['quick_value'] = (
            df['form'].fillna(0) * 0.5 +
            df['points_per_game'].fillna(0) * 0.5
        ) / df['price']
        
        # Players likely to rise with good value
        targets = df[
            (df['rise_probability'] > 40) &
            (df['status'] == 'a') &
            (df['quick_value'] > 0.5)
        ].nlargest(top_n, 'quick_value')
        
        result = targets[[
            'web_name', 'team_short', 'position', 'price',
            'form', 'rise_probability', 'quick_value'
        ]].copy()
        
        print(f"\n{'='*80}")
        print(f"🎯 BEST BUYS BEFORE PRICE RISE (Top {top_n})")
        print(f"{'='*80}")
        print("Get these players NOW before they rise!")
        print(result.to_string(index=False))
        
        return result


# Integration with main app
def add_price_predictor_to_assistant(assistant):
    """Add price prediction features to FPLAssistant"""
    assistant.price_predictor = PriceChangePredictor(assistant.fetcher)
    
    def get_rising_players(top_n=20):
        return assistant.price_predictor.get_rising_players(top_n)
    
    def get_dropping_players(top_n=20):
        return assistant.price_predictor.get_dropping_players(top_n)
    
    def check_my_prices():
        if assistant.my_team is None:
            print("❌ No team loaded!")
            return None
        return assistant.price_predictor.check_my_team_prices(assistant.my_team['player_ids'])
    
    def get_best_buys_before_rise(top_n=15):
        return assistant.price_predictor.get_best_buys_before_rise(top_n)
    
    # Attach methods
    assistant.get_rising_players = get_rising_players
    assistant.get_dropping_players = get_dropping_players
    assistant.check_my_prices = check_my_prices
    assistant.get_best_buys_before_rise = get_best_buys_before_rise
    
    print("\n✅ Price Change Predictor loaded!")


if __name__ == "__main__":
    from fpl_main_app import FPLAssistant
    
    assistant = FPLAssistant()
    assistant.initialize()
    
    # Add price predictor
    add_price_predictor_to_assistant(assistant)
    
    # Test it
    assistant.get_rising_players(top_n=15)
    assistant.get_dropping_players(top_n=15)
    assistant.get_best_buys_before_rise(top_n=10)