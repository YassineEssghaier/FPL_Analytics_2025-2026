"""
FPL Analytics Web Application - Complete Backend with All Features
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from fpl_main_app import FPLAssistant
from price_predictor import PriceChangePredictor, add_price_predictor_to_assistant
from points_predictor import AIPointsPredictor, add_ai_predictor_to_assistant
from live_tracker import LiveGameweekTracker, add_live_tracker_to_assistant
from mini_league import MiniLeagueSpy, add_mini_league_spy_to_assistant
from advanced_fixture_predictor import AdvancedFixturePredictor, add_fixture_predictor_to_assistant
import json
import os

app = Flask(__name__)
CORS(app)

# Global assistant instance
assistant = None

def get_assistant():
    """Get or create assistant instance with ALL features"""
    global assistant
    if assistant is None:
        assistant = FPLAssistant()
        assistant.initialize()
        
        # Add all advanced features
        add_price_predictor_to_assistant(assistant)
        add_ai_predictor_to_assistant(assistant)
        add_live_tracker_to_assistant(assistant)
        add_mini_league_spy_to_assistant(assistant)
        add_fixture_predictor_to_assistant(assistant)
        
        print("✅ ALL features loaded (including Mini-League Spy)!")
    return assistant

@app.route('/')
def home():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/best-players', methods=['GET'])
def best_players():
    """Get best value players"""
    try:
        asst = get_assistant()
        position = request.args.get('position', None)
        top_n = int(request.args.get('top_n', 20))
        
        result = asst.analyzer.recommend_best_players(position=position, top_n=top_n)
        
        return jsonify({
            'success': True,
            'data': result.to_dict('records')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/load-team', methods=['POST'])
def load_team():
    """Load team from FPL"""
    try:
        data = request.json
        manager_id = data.get('manager_id')
        
        if not manager_id:
            return jsonify({'success': False, 'error': 'Manager ID required'}), 400
        
        asst = get_assistant()
        
        # Load team with full manager data
        current_gw = asst.fetcher.get_current_gameweek()
        
        # Fetch manager data
        manager_data = asst.fetcher.fetch_manager_team(manager_id)
        picks_data = asst.fetcher.fetch_manager_picks(manager_id, current_gw)
        
        player_ids = [pick['element'] for pick in picks_data['picks']]
        
        # Try to get history
        try:
            history = asst.fetcher.fetch_manager_history(manager_id)
            current_gw_data = None
            for gw in history['current']:
                if gw['event'] == current_gw:
                    current_gw_data = gw
                    break
            gameweek_points = current_gw_data['points'] if current_gw_data else 0
        except:
            gameweek_points = 0
        
        asst.my_team = {
            'player_ids': player_ids,
            'manager_id': manager_id,
            'manager_name': f"{manager_data.get('player_first_name', '')} {manager_data.get('player_last_name', '')}",
            'total_points': manager_data.get('summary_overall_points', 0),
            'overall_rank': manager_data.get('summary_overall_rank', 0),
            'gameweek_points': gameweek_points,
            'total_transfers': manager_data.get('total_transfers', 0),
            'team_value': manager_data.get('last_deadline_value', 1000) / 10,
        }
        
        # Save to file
        from datetime import datetime
        asst.my_team['saved_at'] = datetime.now().isoformat()
        with open(asst.my_team_file, 'w') as f:
            json.dump(asst.my_team, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Team loaded successfully! (GW {current_gw})',
            'team': asst.my_team
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR loading team: {error_trace}")
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500

@app.route('/api/my-team', methods=['GET'])
def my_team():
    """Get current team summary"""
    try:
        asst = get_assistant()
        
        if asst.my_team is None:
            return jsonify({
                'success': False,
                'error': 'No team saved. Please load your team first.'
            }), 404
        
        team_df = asst.analyzer.players_df[
            asst.analyzer.players_df['id'].isin(asst.my_team['player_ids'])
        ].copy()
        
        return jsonify({
            'success': True,
            'data': {
                'players': team_df.to_dict('records'),
                'manager_name': asst.my_team.get('manager_name', 'N/A'),
                'actual_total_points': asst.my_team.get('total_points', 0),
                'overall_rank': asst.my_team.get('overall_rank', 0),
                'gameweek_points': asst.my_team.get('gameweek_points', 0),
                'total_transfers': asst.my_team.get('total_transfers', 0),
                'team_value': asst.my_team.get('team_value', float(team_df['price'].sum())),
                'avg_value_score': float(team_df['value_score'].mean())
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/transfer-recommendations', methods=['GET'])
def transfer_recommendations():
    """Get transfer recommendations"""
    try:
        asst = get_assistant()
        
        if asst.my_team is None:
            return jsonify({
                'success': False,
                'error': 'No team saved. Please load your team first.'
            }), 404
        
        transfers = int(request.args.get('transfers', 1))
        result = asst.analyzer.recommend_transfers(
            asst.my_team['player_ids'],
            transfers_available=transfers
        )
        
        return jsonify({
            'success': True,
            'data': result.to_dict('records') if len(result) > 0 else []
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/captaincy-picks', methods=['GET'])
def captaincy_picks():
    """Get best captaincy options"""
    try:
        asst = get_assistant()
        top_n = int(request.args.get('top_n', 10))
        
        players_df = asst.analyzer.players_df
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
        
        best_captains = captains.nlargest(top_n, 'captain_score')
        
        return jsonify({
            'success': True,
            'data': best_captains.to_dict('records')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/differentials', methods=['GET'])
def differentials():
    """Get differential picks"""
    try:
        asst = get_assistant()
        ownership = float(request.args.get('ownership', 5.0))
        top_n = int(request.args.get('top_n', 20))
        
        df = asst.analyzer.players_df
        differentials = df[
            (df['selected_by_percent'].astype(float) <= ownership) &
            (df['minutes'] > 180) &
            (df['status'] == 'a')
        ].nlargest(top_n, 'value_score')
        
        return jsonify({
            'success': True,
            'data': differentials.to_dict('records')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search-player', methods=['GET'])
def search_player():
    """Search for a player"""
    try:
        asst = get_assistant()
        name = request.args.get('name', '')
        
        if not name:
            return jsonify({'success': False, 'error': 'Name required'}), 400
        
        df = asst.analyzer.players_df
        results = df[df['web_name'].str.contains(name, case=False, na=False)]
        
        return jsonify({
            'success': True,
            'data': results.to_dict('records')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/compare-players', methods=['POST'])
def compare_players():
    """Compare multiple players"""
    try:
        data = request.json
        player_ids = data.get('player_ids', [])
        
        if not player_ids:
            return jsonify({'success': False, 'error': 'Player IDs required'}), 400
        
        asst = get_assistant()
        df = asst.analyzer.players_df
        players = df[df['id'].isin(player_ids)]
        
        return jsonify({
            'success': True,
            'data': players.to_dict('records')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== PRICE CHANGE FEATURES ==========

@app.route('/api/price-risers', methods=['GET'])
def price_risers():
    """Get players likely to rise in price"""
    try:
        asst = get_assistant()
        top_n = int(request.args.get('top_n', 20))
        result = asst.get_rising_players(top_n)
        return jsonify({'success': True, 'data': result.to_dict('records')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/price-fallers', methods=['GET'])
def price_fallers():
    """Get players likely to drop in price"""
    try:
        asst = get_assistant()
        top_n = int(request.args.get('top_n', 20))
        result = asst.get_dropping_players(top_n)
        return jsonify({'success': True, 'data': result.to_dict('records')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/best-buys-before-rise', methods=['GET'])
def best_buys_before_rise():
    """Get best value players about to rise"""
    try:
        asst = get_assistant()
        top_n = int(request.args.get('top_n', 15))
        result = asst.get_best_buys_before_rise(top_n)
        return jsonify({'success': True, 'data': result.to_dict('records')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-my-prices', methods=['GET'])
def check_my_prices():
    """Check price changes for my team"""
    try:
        asst = get_assistant()
        if asst.my_team is None:
            return jsonify({'success': False, 'error': 'No team loaded'}), 404
        
        result = asst.check_my_prices()
        return jsonify({
            'success': True,
            'data': {
                'rising': result['rising'].to_dict('records') if len(result['rising']) > 0 else [],
                'dropping': result['dropping'].to_dict('records') if len(result['dropping']) > 0 else []
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== AI PREDICTION FEATURES ==========

@app.route('/api/ai-predictions', methods=['GET'])
def ai_predictions():
    """Get AI points predictions"""
    try:
        asst = get_assistant()
        top_n = int(request.args.get('top_n', 30))
        result = asst.predict_next_gameweek(top_n)
        return jsonify({'success': True, 'data': result.to_dict('records')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai-captain', methods=['GET'])
def ai_captain():
    """Get AI captain recommendations"""
    try:
        asst = get_assistant()
        result = asst.predict_captain()
        return jsonify({'success': True, 'data': result.to_dict('records')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai-differentials', methods=['GET'])
def ai_differentials():
    """Get AI differential picks"""
    try:
        asst = get_assistant()
        ownership = float(request.args.get('ownership', 5.0))
        top_n = int(request.args.get('top_n', 15))
        result = asst.predict_differentials(ownership, top_n)
        return jsonify({'success': True, 'data': result.to_dict('records')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai-value-picks', methods=['GET'])
def ai_value_picks():
    """Get AI value for money picks"""
    try:
        asst = get_assistant()
        top_n = int(request.args.get('top_n', 20))
        result = asst.predict_value_picks(top_n)
        return jsonify({'success': True, 'data': result.to_dict('records')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== LIVE TRACKING FEATURES ==========

@app.route('/api/live-team', methods=['GET'])
def live_team():
    """Get live team points"""
    try:
        asst = get_assistant()
        if asst.my_team is None:
            return jsonify({'success': False, 'error': 'No team loaded'}), 404
        
        manager_id = asst.my_team.get('manager_id')
        if not manager_id:
            return jsonify({'success': False, 'error': 'Manager ID not found'}), 404
            
        result = asst.live_tracker.track_my_team_live(manager_id)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bonus-system', methods=['GET'])
def bonus_system():
    """Get current BPS standings"""
    try:
        asst = get_assistant()
        result = asst.show_bps()
        return jsonify({'success': True, 'data': result.to_dict('records')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/team-value', methods=['GET'])
def team_value():
    """Get team value changes"""
    try:
        asst = get_assistant()
        if asst.my_team is None:
            return jsonify({'success': False, 'error': 'No team loaded'}), 404
        
        manager_id = asst.my_team.get('manager_id')
        result = asst.live_tracker.get_price_change_impact(manager_id)
        return jsonify({'success': True, 'data': {'value_change': result}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== MINI-LEAGUE SPY FEATURES ==========

@app.route('/api/analyze-league', methods=['POST'])
def analyze_league():
    """Analyze mini-league standings"""
    try:
        asst = get_assistant()
        data = request.json
        league_id = data.get('league_id')
        
        if not league_id or not asst.my_team:
            return jsonify({'success': False, 'error': 'League ID and team required'}), 400
        
        manager_id = asst.my_team.get('manager_id')
        result = asst.league_spy.analyze_league(league_id, manager_id)
        
        return jsonify({
            'success': True,
            'data': result.to_dict('records')
        })
    except Exception as e:
        import traceback
        print(f"ERROR: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/spy-rival', methods=['POST'])
def spy_rival():
    """Compare against specific rival"""
    try:
        asst = get_assistant()
        data = request.json
        rival_id = data.get('rival_id')
        
        if not rival_id or not asst.my_team:
            return jsonify({'success': False, 'error': 'Rival ID and team required'}), 400
        
        manager_id = asst.my_team.get('manager_id')
        result = asst.league_spy.compare_vs_rival(manager_id, rival_id)
        
        return jsonify({
            'success': True,
            'data': {
                'my_differentials': list(result['my_differentials']),
                'rival_differentials': list(result['rival_differentials']),
                'shared_players': list(result['shared_players']),
                'points_difference': result['points_difference']
            }
        })
    except Exception as e:
        import traceback
        print(f"ERROR: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== STATS ==========
@app.route('/api/team-fixtures', methods=['POST'])
def team_fixtures():
    """Get fixture analysis for a team"""
    try:
        asst = get_assistant()
        data = request.json
        team = data.get('team')
        next_n = int(data.get('next_n', 5))
        
        if not team:
            return jsonify({'success': False, 'error': 'Team required'}), 400
        
        result = asst.get_team_fixtures(team, next_n)
        return jsonify({'success': True, 'data': result.to_dict('records')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/all-fdr', methods=['GET'])
def all_fdr():
    """Get FDR for all teams"""
    try:
        asst = get_assistant()
        next_n = int(request.args.get('next_n', 5))
        result = asst.get_all_fdr(next_n)
        
        # Format for JSON
        formatted = {}
        for team, data in result.items():
            formatted[team] = {
                'avg_fdr': data['avg_fdr'],
                'fixtures': data['fixtures'].to_dict('records')
            }
        
        return jsonify({'success': True, 'data': formatted})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analyze-match', methods=['POST'])
def analyze_match():
    """Analyze specific match"""
    try:
        asst = get_assistant()
        data = request.json
        home_team = data.get('home_team')
        away_team = data.get('away_team')
        
        if not home_team or not away_team:
            return jsonify({'success': False, 'error': 'Both teams required'}), 400
        
        result = asst.analyze_match(home_team, away_team)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify

@app.route('/api/stats', methods=['GET'])
def stats():
    """Get overall statistics"""
    try:
        asst = get_assistant()
        current_gw = asst.fetcher.get_current_gameweek()
        total_players = len(asst.analyzer.players_df)
        
        return jsonify({
            'success': True,
            'data': {
                'current_gameweek': current_gw,
                'total_players': total_players,
                'features_loaded': True
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
    

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 FPL ANALYTICS PRO WEB SERVER STARTING...")
    print("="*80)
    print("\n📍 Open your browser and go to:")
    print("   http://localhost:5000")
    print("\n⏹  Press Ctrl+C to stop the server")
    print("="*80 + "\n")


    
    
    app.run(debug=True, host='0.0.0.0', port=5000)