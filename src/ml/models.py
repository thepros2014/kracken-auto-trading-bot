"""
Machine Learning Models Module
Contains various ML models for trading strategy enhancement
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

logger = logging.getLogger(__name__)

class BaseModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []
        
    def train(self, X: np.ndarray, y: np.ndarray):
        """Train the model"""
        raise NotImplementedError
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions"""
        raise NotImplementedError
    
    def save_model(self, filepath: str):
        """Save model to disk"""
        if self.model is not None:
            joblib.dump({
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'model_name': self.model_name
            }, filepath)
            logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load model from disk"""
        if os.path.exists(filepath):
            data = joblib.load(filepath)
            self.model = data['model']
            self.scaler = data['scaler']
            self.feature_names = data['feature_names']
            self.model_name = data['model_name']
            self.is_trained = True
            logger.info(f"Model loaded from {filepath}")

class RandomForestModel(BaseModel):
    def __init__(self, n_estimators: int = 100, max_depth: int = 10):
        super().__init__("RandomForest")
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42
        )
    
    def train(self, X: np.ndarray, y: np.ndarray):
        """Train Random Forest model"""
        try:
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train model
            self.model.fit(X_scaled, y)
            self.is_trained = True
            
            logger.info(f"Random Forest model trained with {X.shape[0]} samples")
            
        except Exception as e:
            logger.error(f"Error training Random Forest model: {e}")
            raise
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with Random Forest"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        try:
            X_scaled = self.scaler.transform(X)
            return self.model.predict(X_scaled)
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            raise
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get prediction probabilities"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        try:
            X_scaled = self.scaler.transform(X)
            return self.model.predict_proba(X_scaled)
        except Exception as e:
            logger.error(f"Error getting prediction probabilities: {e}")
            raise

class MLStrategyEnhancer:
    def __init__(self, model_type: str = "random_forest"):
        self.model_type = model_type
        self.models = {}
        self.feature_importance = {}
        
    def create_model(self, model_type: str = None):
        """Create a new model instance"""
        model_type = model_type or self.model_type
        
        if model_type == "random_forest":
            return RandomForestModel()
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    def train_model(self, symbol: str, X: np.ndarray, y: np.ndarray, model_type: str = None):
        """Train a model for a specific symbol"""
        model_type = model_type or self.model_type
        
        if symbol not in self.models:
            self.models[symbol] = self.create_model(model_type)
        
        self.models[symbol].train(X, y)
        
        # Store feature importance if available
        if hasattr(self.models[symbol].model, 'feature_importances_'):
            self.feature_importance[symbol] = self.models[symbol].model.feature_importances_
        
        logger.info(f"Model trained for {symbol}")
    
    def predict(self, symbol: str, X: np.ndarray) -> np.ndarray:
        """Make prediction for a symbol"""
        if symbol not in self.models:
            raise ValueError(f"No model trained for symbol {symbol}")
        
        if not self.models[symbol].is_trained:
            raise ValueError(f"Model for {symbol} is not trained")
        
        return self.models[symbol].predict(X)
    
    def predict_proba(self, symbol: str, X: np.ndarray) -> np.ndarray:
        """Get prediction probabilities for a symbol"""
        if symbol not in self.models:
            raise ValueError(f"No model trained for symbol {symbol}")
        
        if not self.models[symbol].is_trained:
            raise ValueError(f"Model for {symbol} is not trained")
        
        return self.models[symbol].predict_proba(X)
    
    def get_feature_importance(self, symbol: str) -> Optional[np.ndarray]:
        """Get feature importance for a symbol"""
        return self.feature_importance.get(symbol)
    
    def save_all_models(self, directory: str):
        """Save all trained models"""
        os.makedirs(directory, exist_ok=True)
        
        for symbol, model in self.models.items():
            if model.is_trained:
                filepath = os.path.join(directory, f"{symbol}_model.joblib")
                model.save_model(filepath)
        
        logger.info(f"All models saved to {directory}")
    
    def load_all_models(self, directory: str):
        """Load all models from directory"""
        if not os.path.exists(directory):
            logger.warning(f"Model directory {directory} does not exist")
            return
        
        for filename in os.listdir(directory):
            if filename.endswith("_model.joblib"):
                symbol = filename.replace("_model.joblib", "")
                filepath = os.path.join(directory, filename)
                
                model = self.create_model()
                model.load_model(filepath)
                self.models[symbol] = model
                
                logger.info(f"Model loaded for {symbol}")

# Feature engineering utilities
class FeatureEngineer:
    @staticmethod
    def create_technical_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create technical indicator features"""
        try:
            # Make a copy to avoid modifying original
            features = df.copy()
            
            # Price-based features
            features['returns'] = features['close'].pct_change()
            features['log_returns'] = np.log(features['close'] / features['close'].shift(1))
            
            # Moving averages
            for window in [5, 10, 20, 50]:
                features[f'sma_{window}'] = features['close'].rolling(window=window).mean()
                features[f'ema_{window}'] = features['close'].ewm(span=window).mean()
                
                # Price relative to MA
                features[f'price_to_sma_{window}'] = features['close'] / features[f'sma_{window}']
                features[f'price_to_ema_{window}'] = features['close'] / features[f'ema_{window}']
            
            # RSI
            delta = features['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            features['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            ema_12 = features['close'].ewm(span=12).mean()
            ema_26 = features['close'].ewm(span=26).mean()
            features['macd'] = ema_12 - ema_26
            features['macd_signal'] = features['macd'].ewm(span=9).mean()
            features['macd_histogram'] = features['macd'] - features['macd_signal']
            
            # Bollinger Bands
            sma_20 = features['close'].rolling(window=20).mean()
            std_20 = features['close'].rolling(window=20).std()
            features['bb_upper'] = sma_20 + (std_20 * 2)
            features['bb_lower'] = sma_20 - (std_20 * 2)
            features['bb_width'] = features['bb_upper'] - features['bb_lower']
            features['bb_position'] = (features['close'] - features['bb_lower']) / features['bb_width']
            
            # Volume features
            features['volume_sma_10'] = features['volume'].rolling(window=10).mean()
            features['volume_ratio'] = features['volume'] / features['volume_sma_10']
            
            # Volatility
            features['volatility'] = features['returns'].rolling(window=10).std()
            
            # Lag features
            for lag in [1, 2, 3, 5]:
                features[f'close_lag_{lag}'] = features['close'].shift(lag)
                features[f'returns_lag_{lag}'] = features['returns'].shift(lag)
                features[f'volume_lag_{lag}'] = features['volume'].shift(lag)
            
            # Drop NaN values
            features = features.dropna()
            
            return features
            
        except Exception as e:
            logger.error(f"Error creating technical features: {e}")
            return df
    
    @staticmethod
    def select_features(df: pd.DataFrame, target_column: str = 'target', 
                       max_features: int = 20) -> Tuple[pd.DataFrame, List[str]]:
        """Select most important features"""
        try:
            # Separate features and target
            feature_columns = [col for col in df.columns if col != target_column]
            X = df[feature_columns]
            y = df[target_column] if target_column in df.columns else None
            
            if y is None:
                # If no target, return all features
                return df, feature_columns
            
            # Use Random Forest to select features
            rf = RandomForestClassifier(n_estimators=50, random_state=42)
            rf.fit(X, y)
            
            # Get feature importance
            importances = rf.feature_importances_
            indices = np.argsort(importances)[::-1]
            
            # Select top features
            top_features = [feature_columns[i] for i in indices[:max_features]]
            
            return df[top_features + [target_column]], top_features
            
        except Exception as e:
            logger.error(f"Error selecting features: {e}")
            return df, [col for col in df.columns if col != target_column]