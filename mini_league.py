"""
Mini-League Spy Tool
Compare your team against all rivals in your mini-league
"""

import pandas as pd
import numpy as np
from datetime import datetime

class MiniLeagueSpy:
    def __init__(self, fetcher, analyzer):
        self.fetcher = fetcher
        self.analyzer = analyzer
        
    def get_league_standings(self, league_id):
        """Get mini-league standings"""
        url = f"{self.fetcher.base_url}leagues-classic/{league_id}/standings/"
        response = self.fetcher.session.get(url)
        return response.json()
    
    def get_all_teams_in_league(self, league_id, page=1):
        """Get all teams in a mini-league (handles pagination)"""
        url = f"{self.fetcher.base_url}leagues-classic/{league_id}/standings/?page_standings={page}"
        response = self.fetcher.session.get(url)
        data = response.json()
        
        teams = data['standings']['results']
        
        # If there are more pages, get them too
        if data['standings']['has_next']:
            teams.extend(self.get_all_teams_in_league(league_id, page + 1))
        
        return teams
    
    def analyze_league(self, league_id, my_manager_id):
        """Complete analysis of mini-league"""
        print(f"\n{'='*80}")
        print(f"⚔️  MINI-LEAGUE SPY ANALYSIS")
        print(f"{'='*80}")
        
        # Get league standings
        league_data = self.get_league_standings(league_id)
        league_name = league_data['league']['name']
        teams = league_data['standings']['results']
        
        print(f"\n🏆 League: {league_name}")
        print(f"👥 Total managers: {len(teams)}")
        
        # Create dataframe
        df = pd.DataFrame(teams)
        
        # Find your position
        my_team = df[df['entry'] == my_manager_id].iloc[0] if len(df[df['entry'] == my_manager_id]) > 0 else None
        
        if my_team is not None:
            print(f"\n📊 YOUR POSITION:")
            print(f"   Rank: {my_team['rank']}/{len(teams)}")
            print(f"   Points: {my_team['total']}")
            print(f"   Team: {my_team['entry_name']} ({my_team['player_name']})")
        
        # Show top 5
        print(f"\n{'='*80}")
        print(f"🥇 TOP 5 IN LEAGUE")
        print(f"{'='*80}")
        top5 = df.head(5)
        print(top5[['rank', 'player_name', 'entry_name', 'total']].to_string(index=False))
        
        return df
    
    def compare_vs_rival(self, my_manager_id, rival_manager_id, gameweek=None):
        """Deep comparison between you and a specific rival"""
        if gameweek is None:
            gameweek = self.fetcher.get_current_gameweek()
        
        print(f"\n{'='*80}")
        print(f"⚔️  HEAD-TO-HEAD COMPARISON (GW {gameweek})")
        print(f"{'='*80}")
        
        # Get both teams
        my_picks = self.fetcher.fetch_manager_picks(my_manager_id, gameweek)
        rival_picks = self.fetcher.fetch_manager_picks(rival_manager_id, gameweek)
        
        my_player_ids = [pick['element'] for pick in my_picks['picks']]
        rival_player_ids = [pick['element'] for pick in rival_picks['picks']]
        
        # Get manager data
        my_data = self.fetcher.fetch_manager_team(my_manager_id)
        rival_data = self.fetcher.fetch_manager_team(rival_manager_id)
        
        print(f"\n👤 YOU: {my_data['player_first_name']} {my_data['player_last_name']}")
        print(f"   Points: {my_data['summary_overall_points']}")
        print(f"   Rank: {my_data['summary_overall_rank']:,}")
        print(f"   Team Value: £{my_data['last_deadline_value']/10:.1f}m")
        
        print(f"\n👤 RIVAL: {rival_data['player_first_name']} {rival_data['player_last_name']}")
        print(f"   Points: {rival_data['summary_overall_points']}")
        print(f"   Rank: {rival_data['summary_overall_rank']:,}")
        print(f"   Team Value: £{rival_data['last_deadline_value']/10:.1f}m")
        
        # Points difference
        points_diff = my_data['summary_overall_points'] - rival_data['summary_overall_points']
        if points_diff > 0:
            print(f"\n✅ You're ahead by {points_diff} points!")
        elif points_diff < 0:
            print(f"\n⚠️  You're behind by {abs(points_diff)} points!")
        else:
            print(f"\n➖ Level on points!")
        
        # Find differentials
        my_differentials = set(my_player_ids) - set(rival_player_ids)
        rival_differentials = set(rival_player_ids) - set(my_player_ids)
        shared_players = set(my_player_ids) & set(rival_player_ids)
        
        print(f"\n{'='*80}")
        print(f"📊 TEAM OVERLAP")
        print(f"{'='*80}")
        print(f"✅ Shared players: {len(shared_players)}/15")
        print(f"💎 Your differentials: {len(my_differentials)}")
        print(f"⚠️  Rival differentials: {len(rival_differentials)}")
        
        # Show differentials with details
        players_df = self.analyzer.players_df
        
        if len(my_differentials) > 0:
            print(f"\n{'='*80}")
            print(f"💎 YOUR DIFFERENTIAL PICKS")
            print(f"{'='*80}")
            my_diff_players = players_df[players_df['id'].isin(my_differentials)]
            print(my_diff_players[['web_name', 'team_short', 'position', 'price', 
                                   'form', 'value_score']].to_string(index=False))
        
        if len(rival_differentials) > 0:
            print(f"\n{'='*80}")
            print(f"⚠️  RIVAL'S DIFFERENTIAL PICKS (Threat Assessment)")
            print(f"{'='*80}")
            rival_diff_players = players_df[players_df['id'].isin(rival_differentials)]
            print(rival_diff_players[['web_name', 'team_short', 'position', 'price', 
                                     'form', 'value_score']].to_string(index=False))
            
            # Identify high-threat players
            high_threat = rival_diff_players[
                (rival_diff_players['form'].astype(float) > 6.0) |
                (rival_diff_players['value_score'] > 0.6)
            ]
            
            if len(high_threat) > 0:
                print(f"\n{'='*80}")
                print(f"🚨 HIGH THREAT: Consider covering these players!")
                print(f"{'='*80}")
                print(high_threat[['web_name', 'team_short', 'form', 
                                  'value_score']].to_string(index=False))
        
        # Captain comparison
        my_captain_id = next((p['element'] for p in my_picks['picks'] if p['is_captain']), None)
        rival_captain_id = next((p['element'] for p in rival_picks['picks'] if p['is_captain']), None)
        
        if my_captain_id and rival_captain_id:
            my_captain = players_df[players_df['id'] == my_captain_id].iloc[0]
            rival_captain = players_df[players_df['id'] == rival_captain_id].iloc[0]
            
            print(f"\n{'='*80}")
            print(f"👑 CAPTAIN COMPARISON")
            print(f"{'='*80}")
            print(f"Your captain: {my_captain['web_name']} ({my_captain['team_short']})")
            print(f"Rival captain: {rival_captain['web_name']} ({rival_captain['team_short']})")
            
            if my_captain_id == rival_captain_id:
                print("➖ Same captain - no differential advantage")
            else:
                print("✅ Different captains - opportunity to gain/lose ground!")
        
        return {
            'my_differentials': my_differentials,
            'rival_differentials': rival_differentials,
            'shared_players': shared_players,
            'points_difference': points_diff
        }
    
    def analyze_entire_league(self, league_id, my_manager_id):
        """Analyze your position vs everyone in the league"""
        print(f"\n{'='*80}")
        print(f"🔍 COMPLETE LEAGUE ANALYSIS")
        print(f"{'='*80}")
        
        # Get all teams
        all_teams = self.get_all_teams_in_league(league_id)
        df = pd.DataFrame(all_teams)
        
        # Get current gameweek
        current_gw = self.fetcher.get_current_gameweek()
        
        # Get all team picks
        print("\n⏳ Analyzing all teams (this may take a moment)...")
        
        league_players = {}
        for team in all_teams[:10]:  # Limit to top 10 for speed
            try:
                manager_id = team['entry']
                picks = self.fetcher.fetch_manager_picks(manager_id, current_gw)
                player_ids = [pick['element'] for pick in picks['picks']]
                league_players[manager_id] = player_ids
            except:
                continue
        
        # Find most popular players in the league
        all_player_ids = []
        for player_list in league_players.values():
            all_player_ids.extend(player_list)
        
        from collections import Counter
        player_counts = Counter(all_player_ids)
        most_common = player_counts.most_common(15)
        
        print(f"\n{'='*80}")
        print(f"📊 MINI-LEAGUE TEMPLATE (Most Owned Players)")
        print(f"{'='*80}")
        
        players_df = self.analyzer.players_df
        template_data = []
        
        for player_id, count in most_common:
            player = players_df[players_df['id'] == player_id]
            if len(player) > 0:
                player = player.iloc[0]
                ownership_pct = (count / len(league_players)) * 100
                template_data.append({
                    'player': player['web_name'],
                    'team': player['team_short'],
                    'position': player['position'],
                    'league_ownership': f"{ownership_pct:.0f}%",
                    'overall_ownership': f"{player['selected_by_percent']}%"
                })
        
        template_df = pd.DataFrame(template_data)
        print(template_df.to_string(index=False))
        
        # Check if you own the template
        my_players = league_players.get(my_manager_id, [])
        template_ids = [pid for pid, _ in most_common]
        
        my_template_count = len(set(my_players) & set(template_ids))
        
        print(f"\n{'='*80}")
        print(f"YOUR TEMPLATE STATUS")
        print(f"{'='*80}")
        print(f"You own {my_template_count}/{len(template_ids)} template players")
        
        if my_template_count >= 10:
            print("⚠️  You're following the template closely - hard to gain ground!")
        elif my_template_count <= 7:
            print("💎 You have significant differentials - high risk/high reward!")
        else:
            print("✅ Good balance of template and differentials")
        
        return template_df
    
    def predict_league_winner(self, league_id):
        """Predict who will win the league based on current form"""
        teams = self.get_all_teams_in_league(league_id)
        df = pd.DataFrame(teams)
        
        # Calculate form-adjusted prediction
        df['predicted_final'] = df['total'] + (df['event_total'] * 10)  # Extrapolate current form
        df = df.sort_values('predicted_final', ascending=False)
        
        print(f"\n{'='*80}")
        print(f"🔮 LEAGUE WINNER PREDICTION")
        print(f"{'='*80}")
        print("Based on current form and points...")
        print(df[['rank', 'player_name', 'total', 'predicted_final']].head(5).to_string(index=False))
        
        return df
    
    def find_weak_rivals(self, league_id):
        """Find rivals you should be able to beat"""
        teams = self.get_all_teams_in_league(league_id)
        df = pd.DataFrame(teams)
        
        # Sort by points
        df = df.sort_values('total', ascending=True)
        
        print(f"\n{'='*80}")
        print(f"🎯 CATCHABLE RIVALS (Lower ranked)")
        print(f"{'='*80}")
        print("Focus on beating these managers:")
        print(df[['rank', 'player_name', 'entry_name', 'total']].head(10).to_string(index=False))
        
        return df


# Integration with main app
def add_mini_league_spy_to_assistant(assistant):
    """Add mini-league spy features to FPLAssistant"""
    assistant.league_spy = MiniLeagueSpy(assistant.fetcher, assistant.analyzer)
    
    def analyze_league(league_id):
        if assistant.my_team is None:
            print("❌ Load your team first!")
            return None
        manager_id = assistant.my_team.get('manager_id')
        return assistant.league_spy.analyze_league(league_id, manager_id)
    
    def spy_on_rival(rival_manager_id):
        if assistant.my_team is None:
            print("❌ Load your team first!")
            return None
        manager_id = assistant.my_team.get('manager_id')
        return assistant.league_spy.compare_vs_rival(manager_id, rival_manager_id)
    
    def analyze_entire_league(league_id):
        if assistant.my_team is None:
            print("❌ Load your team first!")
            return None
        manager_id = assistant.my_team.get('manager_id')
        return assistant.league_spy.analyze_entire_league(league_id, manager_id)
    
    def predict_winner(league_id):
        return assistant.league_spy.predict_league_winner(league_id)
    
    def find_targets(league_id):
        return assistant.league_spy.find_weak_rivals(league_id)
    
    # Attach methods
    assistant.analyze_league = analyze_league
    assistant.spy_on_rival = spy_on_rival
    assistant.analyze_entire_league = analyze_entire_league
    assistant.predict_league_winner = predict_winner
    assistant.find_catchable_rivals = find_targets
    
    print("\n✅ Mini-League Spy Tool loaded!")


if __name__ == "__main__":
    from fpl_main_app import FPLAssistant
    
    assistant = FPLAssistant()
    assistant.initialize()
    assistant.load_my_team_from_fpl(4778515)
    
    # Add spy tool
    add_mini_league_spy_to_assistant(assistant)
    
    # Example usage (replace with your league ID)
    # Find your league ID from URL: https://fantasy.premierleague.com/leagues/YOUR_LEAGUE_ID/standings/c
    LEAGUE_ID = 123456  # Replace with your league ID
    
    # Analyze league
    assistant.analyze_league(LEAGUE_ID)
    
    # Compare vs specific rival
    RIVAL_ID = 654321  # Replace with rival's manager ID
    assistant.spy_on_rival(RIVAL_ID)
    
    # Full league analysis
    assistant.analyze_entire_league(LEAGUE_ID)
    
    # Predict winner
    assistant.predict_league_winner(LEAGUE_ID)