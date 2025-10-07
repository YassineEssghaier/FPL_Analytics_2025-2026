from fpl_main_app import FPLAssistant

# Initialize the system
assistant = FPLAssistant()
assistant.initialize()

# Manually load your team from FPL
manager_id = 4778515
current_gw = assistant.fetcher.get_current_gameweek()

print(f"\n🔄 Loading your team from FPL (Manager ID: {manager_id}, GW: {current_gw})...")

try:
    # Fetch your picks from FPL API
    picks_data = assistant.fetcher.fetch_manager_picks(manager_id, current_gw)
    player_ids = [pick['element'] for pick in picks_data['picks']]
    
    # Save your team
    assistant.save_my_team(player_ids)
    
    print("✅ Team loaded successfully!")
    
    # Show your team
    print("\n" + "="*80)
    print("YOUR TEAM ANALYSIS:")
    print("="*80)
    assistant.get_my_team_summary()
    
    # Get transfer recommendations
    print("\n" + "="*80)
    print("TRANSFER RECOMMENDATIONS:")
    print("="*80)
    assistant.get_transfer_recommendations(transfers_available=1)
    
    # Get captain recommendations
    print("\n" + "="*80)
    print("BEST CAPTAIN PICKS:")
    print("="*80)
    assistant.get_captaincy_picks(top_n=10)
    
except Exception as e:
    print(f"❌ Error loading team: {e}")
    print("Make sure your FPL team is public and you've set your team for this gameweek.")