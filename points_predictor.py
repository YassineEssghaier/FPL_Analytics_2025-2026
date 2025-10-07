"""
AI Points Predictor
Uses machine learning to predict next gameweek points
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

class AIPointsPredictor:
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def prepare_features(self, players_df):
        """Prepare features for ML model"""
        df = players_df.copy()
        
        # Convert to numeric
        numeric_cols = ['form', 'points_per_game', 'minutes', 'goals_scored', 
                       'assists', 'clean_sheets', 'expected_goals', 'expected_assists',
                       'expected_goal_involvements', 'ict_index', 'influence', 
                       'creativity', 'threat', 'bonus', 'bps']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Create derived features
        df['goals_per_90'] = (df['goals_scored'] / (df['minutes'] + 1)) * 90
        df['assists_per_90'] = (df['assists'] / (df['minutes'] + 1)) * 90
        df['xg_per_90'] = (df['expected_goals'] / (df['minutes'] + 1)) * 90
        df['xa_per_90'] = (df['expected_assists'] / (df['minutes'] + 1)) * 90
        df['form_momentum'] = df['form'] * df['points_per_game']
        
        # Position encoding
        position_map = {'GK': 0, 'DEF': 1, 'MID': 2, 'FWD': 3}
        df['position_encoded'] = df['position'].map(position_map)
        
        return df
    
    def train_model(self):
        """Train the ML model on historical data (simulated with current form)"""
        players_df = self.analyzer.players_df.copy()
        
        # Prepare features
        df = self.prepare_features(players_df)
        
        # Feature columns
        feature_cols = [
            'form', 'points_per_game', 'minutes', 'goals_scored', 'assists',
            'expected_goals', 'expected_assists', 'ict_index', 'influence',
            'creativity', 'threat', 'bonus', 'bps', 'goals_per_90', 
            'assists_per_90', 'xg_per_90', 'xa_per_90', 'form_momentum',
            'position_encoded'
        ]
        
        # Filter valid data
        valid_data = df[(df['minutes'] > 90) & (df['form'] > 0)].copy()
        
        if len(valid_data) < 50:
            print("⚠️  Not enough data to train model. Using rule-based predictions.")
            return False
        
        X = valid_data[feature_cols]
        # Target: predict form (proxy for next gameweek points)
        y = valid_data['form']
        
        # Train model
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        
        self.is_trained = True
        print("✅ AI Model trained successfully!")
        return True
    
    def predict_next_gameweek(self, top_n=30):
        """Predict points for next gameweek"""
        if not self.is_trained:
            self.train_model()
        
        players_df = self.analyzer.players_df.copy()
        df = self.prepare_features(players_df)
        
        # Feature columns
        feature_cols = [
            'form', 'points_per_game', 'minutes', 'goals_scored', 'assists',
            'expected_goals', 'expected_assists', 'ict_index', 'influence',
            'creativity', 'threat', 'bonus', 'bps', 'goals_per_90',
            'assists_per_90', 'xg_per_90', 'xa_per_90', 'form_momentum',
            'position_encoded'
        ]
        
        # Predict only for active players with minutes
        valid_players = df[
            (df['status'] == 'a') &
            (df['minutes'] > 90)
        ].copy()
        
        if len(valid_players) == 0:
            print("❌ No valid players to predict")
            return pd.DataFrame()
        
        X = valid_players[feature_cols]
        X_scaled = self.scaler.transform(X)
        
        # Predict
        predictions = self.model.predict(X_scaled)
        
        valid_players['predicted_points'] = np.clip(predictions, 0, 20)
        
        # Confidence based on recent form consistency
        valid_players['confidence'] = np.where(
            valid_players['form'] > 6, 'HIGH',
            np.where(valid_players['form'] > 3, 'MEDIUM', 'LOW')
        )
        
        # Sort by predicted points
        top_predictions = valid_players.nlargest(top_n, 'predicted_points')
        
        result = top_predictions[[
            'web_name', 'team_short', 'position', 'price', 'form',
            'predicted_points', 'confidence', 'selected_by_percent'
        ]].copy()
        
        print(f"\n{'='*80}")
        print(f"🤖 AI POINTS PREDICTIONS - NEXT GAMEWEEK (Top {top_n})")
        print(f"{'='*80}")
        print(result.to_string(index=False))
        
        return result
    
    def predict_captain_options(self, top_n=10):
        """Best captain picks based on AI predictions"""
        predictions = self.predict_next_gameweek(top_n=100)
        
        # Filter premium players (likely captain candidates)
        captains = predictions[predictions['price'] >= 8.0].head(top_n)
        
        print(f"\n{'='*80}")
        print(f"👑 AI CAPTAIN RECOMMENDATIONS (Top {top_n})")
        print(f"{'='*80}")
        print(captains.to_string(index=False))
        
        return captains
    
    def predict_differentials(self, ownership_max=5.0, top_n=15):
        """High predicted points + low ownership = differentials"""
        predictions = self.predict_next_gameweek(top_n=200)
        
        differentials = predictions[
            predictions['selected_by_percent'].astype(float) <= ownership_max
        ].head(top_n)
        
        print(f"\n{'='*80}")
        print(f"💎 AI DIFFERENTIAL PICKS (Under {ownership_max}% ownership)")
        print(f"{'='*80}")
        print(differentials.to_string(index=False))
        
        return differentials
    
    def compare_prediction_vs_price(self, top_n=20):
        """Find best value: high predictions, low price"""
        predictions = self.predict_next_gameweek(top_n=200)
        
        predictions['value_ratio'] = predictions['predicted_points'] / predictions['price']
        
        best_value = predictions.nlargest(top_n, 'value_ratio')
        
        print(f"\n{'='*80}")
        print(f"💰 BEST VALUE FOR MONEY (Top {top_n})")
        print(f"{'='*80}")
        print(best_value[[
            'web_name', 'team_short', 'position', 'price',
            'predicted_points', 'value_ratio', 'confidence'
        ]].to_string(index=False))
        
        return best_value


# Integration with main app
def add_ai_predictor_to_assistant(assistant):
    """Add AI prediction features to FPLAssistant"""
    assistant.ai_predictor = AIPointsPredictor(assistant.analyzer)
    
    def predict_next_gameweek(top_n=30):
        return assistant.ai_predictor.predict_next_gameweek(top_n)
    
    def predict_captain():
        return assistant.ai_predictor.predict_captain_options(top_n=10)
    
    def predict_differentials(ownership_max=5.0, top_n=15):
        return assistant.ai_predictor.predict_differentials(ownership_max, top_n)
    
    def predict_value_picks(top_n=20):
        return assistant.ai_predictor.compare_prediction_vs_price(top_n)
    
    # Attach methods
    assistant.predict_next_gameweek = predict_next_gameweek
    assistant.predict_captain = predict_captain
    assistant.predict_differentials = predict_differentials
    assistant.predict_value_picks = predict_value_picks
    
    print("\n✅ AI Points Predictor loaded!")


if __name__ == "__main__":
    from fpl_main_app import FPLAssistant
    
    assistant = FPLAssistant()
    assistant.initialize()
    
    # Add AI predictor
    add_ai_predictor_to_assistant(assistant)
    
    # Test predictions
    assistant.predict_next_gameweek(top_n=20)
    assistant.predict_captain()
    assistant.predict_differentials(ownership_max=5.0, top_n=15)
    assistant.predict_value_picks(top_n=15)