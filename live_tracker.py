"""
Live Gameweek Tracker
Track your team's points in real-time during matches
"""

import pandas as pd
import requests
from datetime import datetime

class LiveGameweekTracker:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.base_url = "https://fantasy.premierleague.com/api/"
        
    def get_live_points(self, gameweek=None):
        """Get live points for current gameweek"""
        if gameweek is None:
            gameweek = self.fetcher.get_current_gameweek()
        
        url = f"{self.base_url}event/{gameweek}/live/"
        response = requests.get(url)
        return response.json()
    
    def track_my_team_live(self, manager_id, gameweek=None):
        """Track your team's live points"""
        if gameweek is None:
            gameweek = self.fetcher.get_current_gameweek()
        
        # Get your picks
        picks_data = self.fetcher.fetch_manager_picks(manager_id, gameweek)
        my_picks = picks_data['picks']
        
        # Get live data
        live_data = self.get_live_points(gameweek)
        live_elements = {elem['id']: elem for elem in live_data['elements']}
        
        # Get player details
        bootstrap = self.fetcher.fetch_bootstrap_data()
        all_players = {p['id']: p for p in bootstrap['elements']}
        
        # Calculate live points
        team_live = []
        total_points = 0
        
        for pick in my_picks:
            player_id = pick['element']
            player_live = live_elements.get(player_id, {})
            player_info = all_players.get(player_id, {})
            
            # Get live stats
            stats = player_live.get('stats', {})
            live_points = stats.get('total_points', 0)
            
            # Apply captain multiplier
            multiplier = pick['multiplier']
            final_points = live_points * multiplier
            
            team_live.append({
                'name': player_info.get('web_name', 'Unknown'),
                'position': pick['position'],
                'is_captain': multiplier == 2,
                'is_vice': pick['is_vice_captain'],
                'live_points': live_points,
                'multiplier': multiplier,
                'final_points': final_points,
                'minutes': stats.get('minutes', 0),
                'goals': stats.get('goals_scored', 0),
                'assists': stats.get('assists', 0),
                'clean_sheets': stats.get('clean_sheets', 0),
                'bonus': stats.get('bonus', 0),
                'bps': stats.get('bps', 0)
            })
            
            # Only count starting 11
            if pick['position'] <= 11:
                total_points += final_points
        
        return {
            'gameweek': gameweek,
            'total_points': total_points,
            'team': team_live,
            'timestamp': datetime.now().isoformat()
        }
    
    def display_live_team(self, manager_id, gameweek=None):
        """Display live team with nice formatting"""
        live_data = self.track_my_team_live(manager_id, gameweek)
        
        print(f"\n{'='*100}")
        print(f"⚡ LIVE GAMEWEEK {live_data['gameweek']} TRACKER")
        print(f"{'='*100}")
        print(f"🔴 LIVE POINTS: {live_data['total_points']}")
        print(f"⏰ Last updated: {datetime.now().strftime('%H:%M:%S')}")
        print(f"\n{'-'*100}")
        
        df = pd.DataFrame(live_data['team'])
        
        # Separate starting 11 and bench
        starting = df[df['position'] <= 11].sort_values('position')
        bench = df[df['position'] > 11].sort_values('position')
        
        print("\n⭐ STARTING 11:")
        print(starting[[
            'name', 'live_points', 'multiplier', 'final_points',
            'minutes', 'goals', 'assists', 'bonus'
        ]].to_string(index=False))
        
        print(f"\n📋 BENCH:")
        print(bench[[
            'name', 'live_points', 'minutes', 'goals', 'assists'
        ]].to_string(index=False))
        
        # Highlight captain
        captain = df[df['is_captain']].iloc[0] if len(df[df['is_captain']]) > 0 else None
        if captain is not None:
            print(f"\n👑 CAPTAIN: {captain['name']} - {captain['final_points']} points (x2)")
        
        return live_data
    
    def get_bonus_points_system(self, gameweek=None):
        """Get current BPS (Bonus Points System) standings"""
        if gameweek is None:
            gameweek = self.fetcher.get_current_gameweek()
        
        live_data = self.get_live_points(gameweek)
        
        # Get players with BPS
        bps_data = []
        for elem in live_data['elements']:
            stats = elem.get('stats', {})
            bps = stats.get('bps', 0)
            
            if bps > 0:
                bps_data.append({
                    'player_id': elem['id'],
                    'bps': bps,
                    'bonus': stats.get('bonus', 0),
                    'minutes': stats.get('minutes', 0)
                })
        
        bps_df = pd.DataFrame(bps_data).sort_values('bps', ascending=False)
        
        print(f"\n{'='*80}")
        print(f"🎁 BONUS POINTS SYSTEM (BPS) - LIVE STANDINGS")
        print(f"{'='*80}")
        print(bps_df.head(20).to_string(index=False))
        
        return bps_df
    
    def get_price_change_impact(self, manager_id):
        """Calculate potential team value gains/losses"""
        # Get team
        current_gw = self.fetcher.get_current_gameweek()
        picks_data = self.fetcher.fetch_manager_picks(manager_id, current_gw)
        player_ids = [pick['element'] for pick in picks_data['picks']]
        
        # Get player data
        bootstrap = self.fetcher.fetch_bootstrap_data()
        all_players = pd.DataFrame(bootstrap['elements'])
        
        my_team = all_players[all_players['id'].isin(player_ids)].copy()
        
        # Calculate value changes
        my_team['cost_change_event'] = pd.to_numeric(my_team['cost_change_event'], errors='coerce')
        total_change = my_team['cost_change_event'].sum() / 10  # Convert to millions
        
        print(f"\n{'='*80}")
        print(f"💰 TEAM VALUE TRACKER")
        print(f"{'='*80}")
        print(f"Team value change this GW: £{total_change:.1f}m")
        
        if total_change > 0:
            print(f"✅ Your team gained value! (+£{total_change:.1f}m)")
        elif total_change < 0:
            print(f"⚠️  Your team lost value! (£{total_change:.1f}m)")
        else:
            print("➖ No value change this gameweek")
        
        return total_change
    
    def get_differential_performance(self, manager_id):
        """See how your differentials are performing"""
        live_data = self.track_my_team_live(manager_id)
        
        # Get ownership data
        bootstrap = self.fetcher.fetch_bootstrap_data()
        all_players = {p['id']: p for p in bootstrap['elements']}
        
        differentials = []
        for player in live_data['team']:
            player_id = next((p['element'] for p in self.fetcher.fetch_manager_picks(
                manager_id, live_data['gameweek'])['picks'] 
                if all_players.get(p['element'], {}).get('web_name') == player['name']), None)
            
            if player_id:
                ownership = float(all_players.get(player_id, {}).get('selected_by_percent', 0))
                
                if ownership < 10:  # Differential threshold
                    differentials.append({
                        'name': player['name'],
                        'ownership': ownership,
                        'points': player['final_points'],
                        'is_captain': player['is_captain']
                    })
        
        if differentials:
            print(f"\n{'='*80}")
            print(f"💎 YOUR DIFFERENTIALS PERFORMANCE")
            print(f"{'='*80}")
            df = pd.DataFrame(differentials)
            print(df.to_string(index=False))
        else:
            print("\n➖ No differentials in your team")
        
        return differentials


# Integration with main app
def add_live_tracker_to_assistant(assistant):
    """Add live tracking features to FPLAssistant"""
    assistant.live_tracker = LiveGameweekTracker(assistant.fetcher)
    
    def track_live():
        if assistant.my_team is None:
            print("❌ No team loaded!")
            return None
        manager_id = assistant.my_team.get('manager_id')
        if not manager_id:
            print("❌ Manager ID not found in saved team!")
            return None
        return assistant.live_tracker.display_live_team(manager_id)
    
    def show_bps():
        return assistant.live_tracker.get_bonus_points_system()
    
    def check_team_value():
        if assistant.my_team is None:
            print("❌ No team loaded!")
            return None
        manager_id = assistant.my_team.get('manager_id')
        if not manager_id:
            print("❌ Manager ID not found!")
            return None
        return assistant.live_tracker.get_price_change_impact(manager_id)
    
    def check_differentials():
        if assistant.my_team is None:
            print("❌ No team loaded!")
            return None
        manager_id = assistant.my_team.get('manager_id')
        if not manager_id:
            print("❌ Manager ID not found!")
            return None
        return assistant.live_tracker.get_differential_performance(manager_id)
    
    # Attach methods
    assistant.track_live = track_live
    assistant.show_bps = show_bps
    assistant.check_team_value = check_team_value
    assistant.check_differentials = check_differentials
    
    print("\n✅ Live Gameweek Tracker loaded!")


if __name__ == "__main__":
    from fpl_main_app import FPLAssistant
    
    assistant = FPLAssistant()
    assistant.initialize()
    
    # Load your team
    assistant.load_my_team_from_fpl(4778515)
    
    # Add live tracker
    add_live_tracker_to_assistant(assistant)
    
    # Track live
    assistant.track_live()
    assistant.show_bps()
    assistant.check_team_value()
    assistant.check_differentials()