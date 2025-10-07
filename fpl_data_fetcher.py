"""
FPL Data Fetcher - Fetches all necessary data from official FPL API
"""

import requests
import pandas as pd
import json
from datetime import datetime
import time

class FPLDataFetcher:
    def __init__(self):
        self.base_url = "https://fantasy.premierleague.com/api/"
        self.session = requests.Session()
        
    def fetch_bootstrap_data(self):
        """
        Fetch the main bootstrap-static data containing:
        - All players
        - All teams
        - Game settings
        - Current gameweek info
        """
        url = f"{self.base_url}bootstrap-static/"
        response = self.session.get(url)
        return response.json()
    
    def fetch_player_details(self, player_id):
        """Fetch detailed data for a specific player"""
        url = f"{self.base_url}element-summary/{player_id}/"
        response = self.session.get(url)
        return response.json()
    
    def fetch_fixtures(self):
        """Fetch all fixtures data"""
        url = f"{self.base_url}fixtures/"
        response = self.session.get(url)
        return response.json()
    
    def fetch_manager_team(self, manager_id):
        """Fetch a specific manager's team"""
        url = f"{self.base_url}entry/{manager_id}/"
        response = self.session.get(url)
        return response.json()
    
    def fetch_manager_history(self, manager_id):
        """Fetch manager's gameweek history"""
        url = f"{self.base_url}entry/{manager_id}/history/"
        response = self.session.get(url)
        return response.json()
    
    def fetch_manager_picks(self, manager_id, gameweek):
        """Fetch manager's picks for a specific gameweek"""
        url = f"{self.base_url}entry/{manager_id}/event/{gameweek}/picks/"
        response = self.session.get(url)
        return response.json()
    
    def get_all_players_df(self):
        """Get all players as a pandas DataFrame with relevant stats"""
        data = self.fetch_bootstrap_data()
        players = pd.DataFrame(data['elements'])
        teams = pd.DataFrame(data['teams'])
        
        # Create team mapping
        team_name_map = dict(zip(teams['id'], teams['name']))
        team_short_map = dict(zip(teams['id'], teams['short_name']))
        
        # Add team names to players
        players['team_name'] = players['team'].map(team_name_map)
        players['team_short'] = players['team'].map(team_short_map)
        
        # Select important columns (only those that exist)
        important_cols = [
            'id', 'web_name', 'team_name', 'team_short', 'element_type',
            'now_cost', 'total_points', 'points_per_game', 'selected_by_percent',
            'form', 'minutes', 'goals_scored', 'assists', 'clean_sheets',
            'goals_conceded', 'bonus', 'bps', 'influence', 'creativity', 
            'threat', 'ict_index', 'expected_goals', 'expected_assists',
            'expected_goal_involvements', 'expected_goals_conceded',
            'news', 'chance_of_playing_next_round', 'status'
        ]
        
        # Only select columns that actually exist in the dataframe
        available_cols = [col for col in important_cols if col in players.columns]
        players_clean = players[available_cols].copy()
        
        # Convert price from tenths to actual price
        players_clean['price'] = players_clean['now_cost'] / 10
        
        # Add position names
        position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        players_clean['position'] = players_clean['element_type'].map(position_map)
        
        return players_clean
    
    def get_fixtures_df(self):
        """Get fixtures as a DataFrame"""
        fixtures = self.fetch_fixtures()
        fixtures_df = pd.DataFrame(fixtures)
        
        # Get team names
        data = self.fetch_bootstrap_data()
        teams = pd.DataFrame(data['teams'])
        team_map = dict(zip(teams['id'], teams['short_name']))
        
        fixtures_df['home_team'] = fixtures_df['team_h'].map(team_map)
        fixtures_df['away_team'] = fixtures_df['team_a'].map(team_map)
        
        return fixtures_df
    
    def get_current_gameweek(self):
        """Get the current gameweek number"""
        data = self.fetch_bootstrap_data()
        events = data['events']
        for event in events:
            if event['is_current']:
                return event['id']
        return None
    
    def save_data_locally(self, filename='fpl_data.json'):
        """Save all data locally for offline analysis"""
        data = {
            'bootstrap': self.fetch_bootstrap_data(),
            'fixtures': self.fetch_fixtures(),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Data saved to {filename}")
        return data


# Example usage
if __name__ == "__main__":
    fetcher = FPLDataFetcher()
    
    print("Fetching FPL data...")
    players_df = fetcher.get_all_players_df()
    
    print(f"\nTotal players: {len(players_df)}")
    print("\nTop 10 players by total points:")
    print(players_df.nlargest(10, 'total_points')[['web_name', 'team_short', 'position', 'price', 'total_points', 'form']])
    
    print(f"\nCurrent Gameweek: {fetcher.get_current_gameweek()}")
    
    # Save data locally
    fetcher.save_data_locally()