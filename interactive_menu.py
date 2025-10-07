"""
FPL Analytics - Interactive Menu (Working Version)
"""

from fpl_main_app import FPLAssistant

def print_menu():
    print("\n" + "="*80)
    print("🏆 FPL ANALYTICS INTERACTIVE MENU")
    print("="*80)
    print("""
1.  Show best players overall
2.  Show best players by position (GK/DEF/MID/FWD)
3.  Build optimal 15-player squad
4.  Save my current team (manual entry)
5.  Get transfer recommendations
6.  Search for a player
7.  Compare players
8.  View my team summary
9.  Find differential picks
10. Get captaincy recommendations
11. View fixture analysis
12. Find template breakers
13. Show best budget options (under £6.0m)
14. Show best premium players (£9.0m+)

0.  Exit
    """)
    print("="*80)

def main():
    print("\n🚀 Initializing FPL Analytics System...")
    assistant = FPLAssistant()
    assistant.initialize()
    
    while True:
        print_menu()
        choice = input("👉 Enter your choice (0-14): ").strip()
        
        try:
            if choice == '1':
                print("\n" + "="*80)
                print("TOP 20 BEST VALUE PLAYERS")
                print("="*80)
                assistant.show_best_players(top_n=20)
                
            elif choice == '2':
                position = input("\n👉 Enter position (GK/DEF/MID/FWD): ").strip().upper()
                if position in ['GK', 'DEF', 'MID', 'FWD']:
                    assistant.show_best_players(position=position, top_n=15)
                else:
                    print("❌ Invalid position! Use GK, DEF, MID, or FWD")
                    
            elif choice == '3':
                budget_input = input("\n👉 Enter budget in millions (press Enter for 100.0): ").strip()
                budget = float(budget_input) if budget_input else 100.0
                assistant.build_best_squad(budget=budget)
                
            elif choice == '4':
                print("\n📝 To save your team, you need 15 player IDs.")
                print("💡 Tip: Use option 6 to search for players and get their IDs\n")
                ids_input = input("👉 Enter 15 player IDs separated by commas: ").strip()
                try:
                    player_ids = [int(x.strip()) for x in ids_input.split(',')]
                    if len(player_ids) == 15:
                        assistant.save_my_team(player_ids)
                    else:
                        print(f"❌ You provided {len(player_ids)} IDs. Need exactly 15!")
                except ValueError:
                    print("❌ Invalid input! Make sure to enter numbers separated by commas")
                    
            elif choice == '5':
                if assistant.my_team is None:
                    print("\n❌ No team saved! Please save your team first (Option 4)")
                    print("💡 Or run: python load_my_team.py to load from FPL")
                else:
                    transfers_input = input("\n👉 How many free transfers do you have? (press Enter for 1): ").strip()
                    transfers = int(transfers_input) if transfers_input else 1
                    assistant.get_transfer_recommendations(transfers_available=transfers)
                    
            elif choice == '6':
                name = input("\n👉 Enter player name to search: ").strip()
                if name:
                    assistant.search_player(name)
                else:
                    print("❌ Please enter a player name!")
                    
            elif choice == '7':
                print("\n💡 Tip: Use option 6 to find player IDs first")
                ids_input = input("\n👉 Enter player IDs to compare (comma-separated): ").strip()
                try:
                    player_ids = [int(x.strip()) for x in ids_input.split(',')]
                    if len(player_ids) >= 2:
                        assistant.compare_players(player_ids)
                    else:
                        print("❌ Please enter at least 2 player IDs to compare!")
                except ValueError:
                    print("❌ Invalid input! Make sure to enter numbers separated by commas")
                    
            elif choice == '8':
                if assistant.my_team is None:
                    print("\n❌ No team saved! Please save your team first (Option 4)")
                    print("💡 Or run: python load_my_team.py to load from FPL")
                else:
                    assistant.get_my_team_summary()
                    
            elif choice == '9':
                ownership_input = input("\n👉 Max ownership % (press Enter for 5.0): ").strip()
                ownership = float(ownership_input) if ownership_input else 5.0
                assistant.get_differentials(ownership_max=ownership, top_n=20)
                
            elif choice == '10':
                print("\n" + "="*80)
                print("👑 BEST CAPTAINCY OPTIONS THIS WEEK")
                print("="*80)
                
                players_df = assistant.analyzer.players_df
                captains = players_df[
                    (players_df['price'] >= 8.0) & 
                    (players_df['status'] == 'a') &
                    (players_df['minutes'] > 450)
                ].copy()
                
                captains['captain_score'] = (
                    captains['form'].astype(float) * 0.4 +
                    captains['points_per_game'].astype(float) * 0.4 +
                    captains['expected_goal_involvements'].astype(float) * 100 * 0.2
                )
                
                best_captains = captains.nlargest(10, 'captain_score')
                print(best_captains[['web_name', 'team_short', 'position', 'price', 
                                     'form', 'points_per_game', 'selected_by_percent']].to_string(index=False))
                
            elif choice == '11':
                print("\n📊 FIXTURE ANALYSIS")
                fixtures_df = assistant.analyzer.fixtures_df
                players_df = assistant.analyzer.players_df
                
                upcoming = fixtures_df[fixtures_df['finished'] == False].copy()
                
                print("\nUpcoming fixtures (next 10 gameweeks):")
                print(upcoming[['event', 'home_team', 'away_team']].head(20).to_string(index=False))
                
            elif choice == '12':
                ownership_input = input("\n👉 Ownership threshold % (press Enter for 30): ").strip()
                ownership = float(ownership_input) if ownership_input else 30.0
                
                players_df = assistant.analyzer.players_df
                template = players_df[
                    players_df['selected_by_percent'].astype(float) >= ownership
                ].sort_values('selected_by_percent', ascending=False)
                
                print(f"\n{'='*80}")
                print(f"⚠️  TEMPLATE PLAYERS (>{ownership}% ownership)")
                print(f"{'='*80}")
                print(template[['web_name', 'team_short', 'position', 'price', 
                               'selected_by_percent', 'value_score']].head(15).to_string(index=False))
                
            elif choice == '13':
                print("\n" + "="*80)
                print("💰 BEST BUDGET OPTIONS (Under £6.0m)")
                print("="*80)
                
                players_df = assistant.analyzer.players_df
                budget = players_df[
                    (players_df['price'] < 6.0) & 
                    (players_df['minutes'] > 180) & 
                    (players_df['status'] == 'a')
                ].nlargest(20, 'value_score')
                
                print(budget[['web_name', 'team_short', 'position', 'price', 
                             'total_points', 'form', 'value_score']].to_string(index=False))
                
            elif choice == '14':
                print("\n" + "="*80)
                print("🌟 BEST PREMIUM PLAYERS (£9.0m+)")
                print("="*80)
                
                players_df = assistant.analyzer.players_df
                premium = players_df[
                    (players_df['price'] >= 9.0) & 
                    (players_df['status'] == 'a')
                ].nlargest(20, 'value_score')
                
                print(premium[['web_name', 'team_short', 'position', 'price', 
                              'total_points', 'form', 'points_per_game', 'value_score']].to_string(index=False))
                
            elif choice == '0':
                print("\n" + "="*80)
                print("👋 Thanks for using FPL Analytics!")
                print("💚 Good luck this gameweek! May your arrows be green! 📈")
                print("="*80)
                break
                
            else:
                print("\n❌ Invalid choice! Please enter a number from 0-14.")
        
        except Exception as e:
            print(f"\n❌ An error occurred: {e}")
            print("Please try again or choose a different option.")
        
        input("\n⏎ Press ENTER to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting... Good luck! 🍀")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your setup and try again.")