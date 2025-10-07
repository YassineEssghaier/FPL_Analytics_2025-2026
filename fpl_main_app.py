"""
FPL Analytics Main Application - UPDATED WITH WINNING FEATURES
Complete system for team selection and transfer recommendations
"""

from fpl_data_fetcher import FPLDataFetcher
from fpl_player_analyzer import FPLPlayerAnalyzer
from fpl_advanced_features import FPLAdvancedAnalyzer
import pandas as pd
import json
from datetime import datetime

class FPLAssistant:
    def __init__(self):
        self.fetcher = FPLDataFetcher()
        self.analyzer = FPLPlayerAnalyzer()
        self.advanced = None
        self.my_team_file = 'my_fpl_team.json'
        self.my_team = None
        
    def initialize(self):
        """Initialize the system by loading data"""
        print("="*80)
        print("🏆 FPL ANALYTICS ASSISTANT - INITIALIZING")
        print("="*80)
        
        self.analyzer.load_data()
        self.analyzer.calculate_value_score()
        
        # Initialize advanced features
        self.advanced = FPLAdvancedAnalyzer(self.analyzer)
        
        # Load saved team if exists
        try:
            with open(self.my_team_file, 'r') as f:
                self.my_team = json.load(f)
            print(f"\n✓ Loaded your saved team from {self.my_team_file}")
        except FileNotFoundError:
            print(f"\n✗ No saved team found. You can save your team using save_my_team()")
        
        print("\n✓ System ready with WINNING FEATURES enabled!")
        print("\n📊 Advanced Features Available:")
        print("  • Captaincy Optimizer")
        print("  • Fixture Analysis (5-8 GW ahead)")
        print("  • Template Breakers")
        print("  • Mini-League Comparison")
        print("  • Wildcard Planner")
        print("  • Bench Boost Optimizer")
        
    def show_best_players(self, position=None, top_n=15):
        """Show best players overall or by position"""
        print(f"\n{'='*80}")
        if position:
            print(f"TOP {top_n} BEST VALUE {position}s")
        else:
            print(f"TOP {top_n} BEST VALUE PLAYERS")
        print("="*80)
        
        result = self.analyzer.recommend_best_players(position=position, top_n=top_n)
        print(result.to_string(index=False))
        return result
    
    def build_best_squad(self, budget=100.0):
        """Build the best possible 15-player squad"""
        return self.analyzer.build_optimal_squad(budget=budget)
    
    def save_my_team(self, player_ids):
        """
        Save your current FPL team
        player_ids: list of 15 player IDs
        """
        if len(player_ids) != 15:
            print(f"Error: You must provide exactly 15 player IDs. You provided {len(player_ids)}")
            return
        
        # Get player details
        team_details = self.analyzer.players_df[
            self.analyzer.players_df['id'].isin(player_ids)
        ][['id', 'web_name', 'team_short', 'position', 'price']].to_dict('records')
        
        self.my_team = {
            'player_ids': player_ids,
            'players': team_details,
            'saved_at': datetime.now().isoformat()
        }
        
        with open(self.my_team_file, 'w') as f:
            json.dump(self.my_team, f, indent=2)
        
        print(f"\n✓ Team saved successfully!")
        print(f"\nYour team ({len(player_ids)} players):")
        for player in team_details:
            print(f"  {player['position']:3} | {player['web_name']:20} | {player['team_short']:3} | £{player['price']:.1f}m")
    
    def load_my_team_from_fpl(self, manager_id, gameweek=None):
        """Load your team directly from FPL API"""
        if gameweek is None:
            gameweek = self.fetcher.get_current_gameweek()
        
        try:
            # Fetch manager data
            manager_data = self.fetcher.fetch_manager_team(manager_id)
            
            # Fetch team picks
            picks_data = self.fetcher.fetch_manager_picks(manager_id, gameweek)
            player_ids = [pick['element'] for pick in picks_data['picks']]
            
            # Fetch history to get actual points
            history = self.fetcher.fetch_manager_history(manager_id)
            
            # Get current gameweek data
            current_gw_data = None
            for gw in history['current']:
                if gw['event'] == gameweek:
                    current_gw_data = gw
                    break
            
            # Get player details
            team_details = self.analyzer.players_df[
                self.analyzer.players_df['id'].isin(player_ids)
            ][['id', 'web_name', 'team_short', 'position', 'price']].to_dict('records')
            
            self.my_team = {
                'player_ids': player_ids,
                'players': team_details,
                'manager_id': manager_id,
                'manager_name': f"{manager_data['player_first_name']} {manager_data['player_last_name']}",
                'total_points': manager_data['summary_overall_points'],  # ACTUAL points with transfers
                'overall_rank': manager_data['summary_overall_rank'],
                'gameweek_points': current_gw_data['points'] if current_gw_data else 0,
                'total_transfers': manager_data['total_transfers'],
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.my_team_file, 'w') as f:
                json.dump(self.my_team, f, indent=2)
            
            print(f"\n✓ Successfully loaded your team from FPL (GW{gameweek})")
            print(f"\n👤 Manager: {self.my_team['manager_name']}")
            print(f"📊 Overall Points: {self.my_team['total_points']} (including transfer hits)")
            print(f"🏆 Overall Rank: {self.my_team['overall_rank']:,}")
            
        except Exception as e:
            print(f"\n✗ Error loading team from FPL: {e}")
            print("Make sure your Manager ID is correct and public.")
    
    def get_transfer_recommendations(self, transfers_available=1):
        """Get transfer recommendations for your saved team"""
        if self.my_team is None:
            print("\n✗ No team saved! Please save your team first using save_my_team()")
            return None
        
        print(f"\n{'='*80}")
        print(f"ANALYZING YOUR TEAM FOR BEST TRANSFERS")
        print(f"{'='*80}")
        print(f"Transfers available: {transfers_available}")
        
        return self.analyzer.recommend_transfers(
            self.my_team['player_ids'], 
            transfers_available=transfers_available
        )
    
    def search_player(self, name):
        """Search for a player by name"""
        df = self.analyzer.players_df
        results = df[df['web_name'].str.contains(name, case=False, na=False)]
        
        if len(results) == 0:
            print(f"\nNo players found matching '{name}'")
            return None
        
        print(f"\n{'='*80}")
        print(f"SEARCH RESULTS FOR: {name}")
        print(f"{'='*80}")
        
        display_cols = ['id', 'web_name', 'team_short', 'position', 'price', 
                       'total_points', 'form', 'value_score', 'status']
        print(results[display_cols].to_string(index=False))
        
        return results
    
    def compare_players(self, player_ids):
        """Compare multiple players side by side"""
        df = self.analyzer.players_df
        players = df[df['id'].isin(player_ids)]
        
        if len(players) == 0:
            print("\nNo players found with those IDs")
            return None
        
        print(f"\n{'='*80}")
        print(f"PLAYER COMPARISON")
        print(f"{'='*80}")
        
        compare_cols = ['web_name', 'team_short', 'position', 'price', 'total_points',
                       'points_per_game', 'form', 'points_per_million', 'selected_by_percent',
                       'expected_goals', 'expected_assists', 'value_score', 'status']
        
        print(players[compare_cols].T.to_string())
        
        return players
    
    def get_my_team_summary(self):
        """Show summary of your current team"""
        if self.my_team is None:
            print("\n✗ No team saved!")
            return None
        
        df = self.analyzer.players_df
        team_df = df[df['id'].isin(self.my_team['player_ids'])].copy()
        
        print(f"\n{'='*80}")
        print(f"YOUR CURRENT FPL TEAM")
        print(f"{'='*80}")
        
        # Show manager info if available
        if 'manager_name' in self.my_team:
            print(f"Manager: {self.my_team['manager_name']}")
            print(f"Overall Points: {self.my_team['total_points']} (ACTUAL - includes transfer hits)")
            print(f"Overall Rank: {self.my_team['overall_rank']:,}")
            print(f"Total Transfers Made: {self.my_team['total_transfers']}")
            print(f"This Gameweek: {self.my_team.get('gameweek_points', 'N/A')} points")
        else:
            print(f"Saved at: {self.my_team['saved_at']}")
            print(f"⚠️  Note: Raw player points shown (doesn't include transfer hits)")
        
        print(f"Team Value: £{team_df['price'].sum():.1f}m")
        print(f"Average value score: {team_df['value_score'].mean():.3f}")
        print(f"\n{'-'*80}")
        
        display_cols = ['web_name', 'team_short', 'position', 'price', 'total_points',
                       'form', 'value_score', 'status', 'news']
        
        print(team_df.sort_values(['position', 'price'], ascending=[True, False])[display_cols].to_string(index=False))
        
        return team_df
    
    def get_differentials(self, ownership_max=5.0, top_n=20):
        """Find differential players (low ownership, high value)"""
        df = self.analyzer.players_df
        
        differentials = df[
            (df['selected_by_percent'].astype(float) <= ownership_max) &
            (df['minutes'] > 180) &
            (df['status'] == 'a')
        ].nlargest(top_n, 'value_score')
        
        print(f"\n{'='*80}")
        print(f"💎 TOP {top_n} DIFFERENTIAL PICKS (≤{ownership_max}% ownership)")
        print(f"{'='*80}")
        
        display_cols = ['web_name', 'team_short', 'position', 'price', 'total_points',
                       'form', 'selected_by_percent', 'value_score']
        print(differentials[display_cols].to_string(index=False))
        
        return differentials
    
    # ========== WINNING FEATURES ==========
    
    def get_captaincy_picks(self, top_n=10):
        """Get best captaincy options for this gameweek"""
        return self.advanced.get_captaincy_picks(top_n)
    
    def get_fixture_analysis(self, next_n_gameweeks=5):
        """Analyze fixture difficulty for all teams"""
        return self.advanced.get_fixture_run_analysis(next_n_gameweeks)
    
    def find_template_breakers(self, ownership_threshold=30.0):
        """Find alternatives to highly owned template players"""
        return self.advanced.find_template_breakers(ownership_threshold)
    
    def compare_vs_rival(self, my_team_ids, rival_team_ids):
        """Compare your team against a rival's team"""
        return self.advanced.mini_league_strategy(my_team_ids, rival_team_ids)
    
    def plan_wildcard(self, budget=100.0, must_have_ids=None):
        """Plan optimal wildcard team"""
        return self.advanced.wildcard_optimizer(budget, must_have_ids)
    
    def plan_bench_boost(self):
        """Analyze when to use Bench Boost chip"""
        return self.advanced.bench_boost_analyzer()


def show_winning_menu():
    """Show the winning features menu"""
    print("\n" + "="*80)
    print("🏆 WINNING FEATURES MENU")
    print("="*80)
    print("""
BASIC FEATURES:
1.  Show best players overall
2.  Show best players by position
3.  Build optimal squad
4.  Search for a player
5.  Save my team
6.  Load my team from FPL (Manager ID)
7.  Get transfer recommendations
8.  View my team summary
9.  Compare players
10. Find differential picks

🔥 WINNING FEATURES:
11. 👑 Get captaincy recommendations (MOST IMPORTANT!)
12. 📊 Fixture analysis (Plan 5-8 GW ahead)
13. 💎 Find template breakers (Differential strategy)
14. ⚔️  Compare vs rival team (Mini-league spy)
15. 🃏 Plan wildcard team
16. 🚀 Plan bench boost timing
17. 💰 Best budget options (Under £6.0m)
18. 🌟 Best premium players (£9.0m+)

0.  Exit
    """)


def main():
    """Main function with winning features"""
    
    # Initialize the assistant
    assistant = FPLAssistant()
    assistant.initialize()
    
    # Show what we can do
    show_winning_menu()
    
    # Example usage - WINNING STRATEGY
    print("\n" + "="*80)
    print("🎯 QUICK START - WINNING THIS GAMEWEEK")
    print("="*80)
    print("\nRunning essential winning analysis...\n")
    
    # 1. Best captaincy picks
    print("\n👑 STEP 1: CAPTAINCY (40% of your score!)")
    assistant.get_captaincy_picks(top_n=10)
    
    # 2. Fixture analysis
    print("\n📊 STEP 2: FIXTURE PLANNING")
    assistant.get_fixture_analysis(next_n_gameweeks=5)
    
    # 3. Best differentials
    print("\n💎 STEP 3: DIFFERENTIAL OPPORTUNITIES")
    assistant.get_differentials(ownership_max=5.0, top_n=15)
    
    # 4. Template breakers
    print("\n🎯 STEP 4: TEMPLATE ANALYSIS")
    assistant.find_template_breakers(ownership_threshold=30.0)
    
    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE!")
    print("="*80)
    print("\nNext steps:")
    print("1. Save your team: assistant.save_my_team([player_ids])")
    print("2. Get transfers: assistant.get_transfer_recommendations()")
    print("3. Compare vs rival: assistant.compare_vs_rival(my_ids, rival_ids)")
    print("4. Make your moves on FPL website!")
    
    # Uncomment below for interactive usage:
    """
    while True:
        show_winning_menu()
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '1':
            assistant.show_best_players(top_n=20)
        elif choice == '2':
            position = input("Position (GK/DEF/MID/FWD): ").strip().upper()
            assistant.show_best_players(position=position, top_n=15)
        elif choice == '3':
            assistant.build_best_squad(budget=100.0)
        elif choice == '4':
            name = input("Player name: ").strip()
            assistant.search_player(name)
        elif choice == '5':
            ids = input("Enter 15 player IDs (comma-separated): ").strip()
            player_ids = [int(x.strip()) for x in ids.split(',')]
            assistant.save_my_team(player_ids)
        elif choice == '6':
            manager_id = int(input("Your Manager ID: ").strip())
            assistant.load_my_team_from_fpl(manager_id)
        elif choice == '7':
            transfers = int(input("Free transfers (default 1): ").strip() or "1")
            assistant.get_transfer_recommendations(transfers)
        elif choice == '8':
            assistant.get_my_team_summary()
        elif choice == '9':
            ids = input("Player IDs to compare (comma-separated): ").strip()
            player_ids = [int(x.strip()) for x in ids.split(',')]
            assistant.compare_players(player_ids)
        elif choice == '10':
            ownership = float(input("Max ownership % (default 5.0): ").strip() or "5.0")
            assistant.get_differentials(ownership, top_n=20)
        elif choice == '11':
            assistant.get_captaincy_picks(top_n=10)
        elif choice == '12':
            gw = int(input("How many GWs ahead? (default 5): ").strip() or "5")
            assistant.get_fixture_analysis(gw)
        elif choice == '13':
            ownership = float(input("Ownership threshold % (default 30): ").strip() or "30")
            assistant.find_template_breakers(ownership)
        elif choice == '14':
            print("Get rival's team from their FPL profile URL")
            rival_id = int(input("Rival's Manager ID: ").strip())
            if assistant.my_team:
                rival_gw = assistant.fetcher.get_current_gameweek()
                rival_picks = assistant.fetcher.fetch_manager_picks(rival_id, rival_gw)
                rival_ids = [p['element'] for p in rival_picks['picks']]
                assistant.compare_vs_rival(assistant.my_team['player_ids'], rival_ids)
            else:
                print("Save your team first!")
        elif choice == '15':
            budget = float(input("Budget (default 100.0): ").strip() or "100")
            assistant.plan_wildcard(budget)
        elif choice == '16':
            assistant.plan_bench_boost()
        elif choice == '17':
            df = assistant.analyzer.players_df
            budget = df[(df['price'] < 6.0) & (df['minutes'] > 180)]
            print(budget.nlargest(20, 'value_score')[['web_name', 'team_short', 
                  'position', 'price', 'form', 'value_score']])
        elif choice == '18':
            df = assistant.analyzer.players_df
            premium = df[(df['price'] >= 9.0) & (df['status'] == 'a')]
            print(premium.nlargest(20, 'value_score')[['web_name', 'team_short',
                  'position', 'price', 'form', 'value_score']])
        elif choice == '0':
            print("\n👋 Good luck! May your arrows be green! 📈🍀")
            break
        else:
            print("Invalid choice!")
        
        input("\n⏎ Press Enter to continue...")
    """


if __name__ == "__main__":
    main()