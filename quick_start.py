"""
FPL Analytics - Quick Start Interactive Script
Run this for an easy interactive experience!
"""

from fpl_main_app import FPLAssistant

def print_menu():
    print("\n" + "="*80)
    print("🏆 FPL ANALYTICS ASSISTANT 🏆")
    print("="*80)
    print("""
Choose an option:

1️⃣  - Show top 20 best value players (all positions)
2️⃣  - Show best players by position (GK/DEF/MID/FWD)
3️⃣  - Build optimal 15-player squad
4️⃣  - Search for a specific player
5️⃣  - Save my current team
6️⃣  - Load my team from FPL (using Manager ID)
7️⃣  - Get transfer recommendations
8️⃣  - View my team summary
9️⃣  - Compare multiple players
🔟 - Find differential picks (low ownership gems)
1️⃣1️⃣ - Show best budget options (under £6.0m)
1️⃣2️⃣ - Show premium players (£9.0m+)
    
0️⃣  - Exit

    """)
    print("="*80)

def main():
    print("\n🚀 Initializing FPL Analytics System...")
    assistant = FPLAssistant()
    assistant.initialize()
    
    while True:
        print_menu()
        choice = input("Enter your choice: ").strip()
        
        if choice == '1':
            assistant.show_best_players(top_n=20)
            
        elif choice == '2':
            position = input("Enter position (GK/DEF/MID/FWD): ").strip().upper()
            if position in ['GK', 'DEF', 'MID', 'FWD']:
                assistant.show_best_players(position=position, top_n=15)
            else:
                print("❌ Invalid position! Use GK, DEF, MID, or FWD")
                
        elif choice == '3':
            budget = input("Enter budget in millions (default 100.0): ").strip()
            budget = float(budget) if budget else 100.0
            assistant.build_best_squad(budget=budget)
            
        elif choice == '4':
            name = input("Enter player name to search: ").strip()
            assistant.search_player(name)
            
        elif choice == '5':
            print("\nTo save your team, you need 15 player IDs.")
            print("Tip: Use option 4 to search for players and get their IDs\n")
            ids_input = input("Enter 15 player IDs separated by commas: ").strip()
            try:
                player_ids = [int(x.strip()) for x in ids_input.split(',')]
                if len(player_ids) == 15:
                    assistant.save_my_team(player_ids)
                else:
                    print(f"❌ You provided {len(player_ids)} IDs. Need exactly 15!")
            except ValueError:
                print("❌ Invalid input! Make sure to enter numbers separated by commas")
                
        elif choice == '6':
            manager_id = input("Enter your FPL Manager ID: ").strip()
            try:
                manager_id = int(manager_id)
                # This requires adding the method to FPLAssistant - for now show message
                print("\n💡 To use this feature, add the load_my_team_from_fpl method")
                print("   Check the setup guide for instructions!")
            except ValueError:
                print("❌ Invalid Manager ID! Must be a number")
                
        elif choice == '7':
            transfers = input("How many free transfers do you have? (default 1): ").strip()
            transfers = int(transfers) if transfers else 1
            assistant.get_transfer_recommendations(transfers_available=transfers)
            
        elif choice == '8':
            assistant.get_my_team_summary()
            
        elif choice == '9':
            ids_input = input("Enter player IDs to compare (comma-separated): ").strip()
            try:
                player_ids = [int(x.strip()) for x in ids_input.split(',')]
                assistant.compare_players(player_ids)
            except ValueError:
                print("❌ Invalid input! Make sure to enter numbers separated by commas")
                
        elif choice == '10':
            ownership = input("Max ownership % (default 5.0): ").strip()
            ownership = float(ownership) if ownership else 5.0
            assistant.get_differentials(ownership_max=ownership, top_n=20)
            
        elif choice == '11':
            print("\n" + "="*80)
            print("BEST BUDGET OPTIONS (Under £6.0m)")
            print("="*80)
            df = assistant.analyzer.players_df
            budget = df[(df['price'] < 6.0) & (df['minutes'] > 180) & (df['status'] == 'a')]
            budget = budget.nlargest(20, 'value_score')
            display_cols = ['web_name', 'team_short', 'position', 'price', 
                          'total_points', 'form', 'value_score']
            print(budget[display_cols].to_string(index=False))
            
        elif choice == '12':
            print("\n" + "="*80)
            print("BEST PREMIUM PLAYERS (£9.0m+)")
            print("="*80)
            df = assistant.analyzer.players_df
            premium = df[(df['price'] >= 9.0) & (df['status'] == 'a')]
            premium = premium.nlargest(20, 'value_score')
            display_cols = ['web_name', 'team_short', 'position', 'price', 
                          'total_points', 'form', 'points_per_game', 'value_score']
            print(premium[display_cols].to_string(index=False))
            
        elif choice == '0':
            print("\n👋 Thanks for using FPL Analytics! Good luck this gameweek! 🍀")
            break
            
        else:
            print("❌ Invalid choice! Please enter a number from the menu.")
        
        input("\n⏎ Press Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting... Good luck! 🍀")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your setup and try again.")