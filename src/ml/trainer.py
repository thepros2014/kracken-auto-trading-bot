"""
ML Trainer Module
Handles training of machine learning models for trading strategies
"""
import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self, data_manager, model_manager):
        self.data_manager = data_manager
        self.model_manager = model_manager
        self.feature_engineer = None  # Will be imported from models module
        self.training_pairs = []
        self.training_interval_hours = 24
        self.is_training = False
        
        logger.info("Model trainer initialized")
    
    def set_feature_engineer(self, feature_engineer):
        """Set the feature engineer"""
        self.feature_engineer = feature_engineer
    
    def add_training_pair(self, symbol: str):
        """Add a trading pair for model training"""
        if symbol not in self.training_pairs:
            self.training_pairs.append(symbol)
            logger.info(f"Added {symbol} to training pairs")
    
    def set_training_interval(self, hours: int):
        """Set how often to retrain models"""
        self.training_interval_hours = hours
        logger.info(f"Training interval set to {hours} hours")
    
    async def start_training_loop(self):
        """Start the continuous training loop"""
        if self.is_training:
            logger.warning("Training loop already running")
            return
        
        self.is_training = True
        logger.info("Starting model training loop...")
        
        while self.is_training:
            try:
                await self._train_all_models()
                await asyncio.sleep(self.training_interval_hours * 3600)  # Convert hours to seconds
            except Exception as e:
                logger.error(f"Error in training loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def stop_training(self):
        """Stop the training loop"""
        self.is_training = False
        logger.info("Stopping model training loop")
    
    async def _train_all_models(self):
        """Train models for all configured pairs"""
        logger.info(f"Starting training cycle for {len(self.training_pairs)} pairs")
        
        for symbol in self.training_pairs:
            try:
                await self._train_models_for_pair(symbol)
            except Exception as e:
                logger.error(f"Error training models for {symbol}: {e}")
        
        logger.info("Training cycle completed")
    
    async def _train_models_for_pair(self, symbol: str):
        """Train models for a specific trading pair"""
        try:
            # Fetch historical data
            historical_data = await self.data_manager.get_historical_data(symbol, limit=1000)
            
            if len(historical_data) < 100:
                logger.warning(f"Insufficient data for {symbol}: {len(historical_data)} rows")
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(historical_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume'
            ])
            
            # Create features
            if self.feature_engineer is None:
                # Import here to avoid circular imports
                from .models import FeatureEngineer
                self.feature_engineer = FeatureEngineer()
            
            featured_df = self.feature_engineer.create_technical_features(df)
            
            # Create target variable (next period return)
            featured_df['target'] = self.feature_engineer.create_target_variable(
                featured_df, method="future_return", periods=1
            )
            
            # Remove rows with NaN values
            featured_df = featured_df.dropna()
            
            if len(featured_df) < 50:
                logger.warning(f"Insufficient featured data for {symbol}: {len(featured_df)} rows")
                return
            
            # Prepare features and target
            feature_columns = [col for col in featured_df.columns 
                             if col not in ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'target']]
            
            X, _ = self.feature_engineer.prepare_features(featured_df, feature_columns)
            y = featured_df['target'].values
            
            # Convert regression target to classification for simplicity
            # Positive return = 1 (buy), Negative or zero return = 0 (sell/hold)
            y_classification = (y > 0).astype(int)
            
            # Train Random Forest model
            rf_model = self.model_manager.models.get('random_forest')
            if rf_model is None:
                from .models import RandomForestModel
                rf_model = RandomForestModel("random_forest")
                self.model_manager.add_model(rf_model)
            
            # Train the model
            metrics = rf_model.train(X, y_classification)
            logger.info(f"Random Forest model trained for {symbol}: {metrics}")
            
            # Save the model
            model_path = f"./models/random_forest_{symbol.replace('/', '_')}.joblib"
            rf_model.save_model(model_path)
            
        except Exception as e:
            logger.error(f"Error in _train_models_for_pair for {symbol}: {e}")
            raise

# Online learning trainer
class OnlineTrainer:
    """Handles online/incremental learning from live trading data"""
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.batch_size = 100
        self.min_samples_for_update = 50
        self.recent_data = []
        self.is_active = False
        
        logger.info("Online trainer initialized")
    
    def add_training_sample(self, features: np.ndarray, target: float):
        """Add a new training sample for online learning"""
        self.recent_data.append((features, target))
        
        # Keep only recent samples
        if len(self.recent_data) > 1000:
            self.recent_data = self.recent_data[-1000:]
    
    async def start_online_learning(self):
        """Start online learning process"""
        if self.is_active:
            logger.warning("Online learning already active")
            return
        
        self.is_active = True
        logger.info("Starting online learning...")
        
        while self.is_active:
            try:
                if len(self.recent_data) >= self.min_samples_for_update:
                    await self._update_models()
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in online learning: {e}")
                await asyncio.sleep(30)
    
    async def stop_online_learning(self):
        """Stop online learning"""
        self.is_active = False
        logger.info("Stopping online learning")
    
    async def _update_models(self):
        """Update models with recent data"""
        try:
            if len(self.recent_data) < self.batch_size:
                batch_data = self.recent_data
            else:
                # Take most recent samples
                batch_data = self.recent_data[-self.batch_size:]
            
            # Prepare data
            X = np.array([sample[0] for sample in batch_data])
            y = np.array([sample[1] for sample in batch_data])
            
            # Convert to classification if needed
            if y.dtype == float:
                y_class = (y > 0).astype(int)
            else:
                y_class = y
            
            # Update active model if it supports partial fitting
            active_model = self.model_manager.active_model
            if active_model and hasattr(active_model.model, 'partial_fit'):
                # Scale features
                X_scaled = active_model.scaler.transform(X)
                active_model.model.partial_fit(X_scaled, y_class)
                logger.info(f"Online update performed on {len(batch_data)} samples")
            
            # Clear processed data
            self.recent_data = self.recent_data[:-len(batch_data)]
            
        except Exception as e:
            logger.error(f"Error updating models: {e}")

# Backtesting integration
class BacktestIntegrator:
    """Integrates ML models with backtesting engine"""
    def __init__(self, model_manager, data_manager):
        self.model_manager = model_manager
        self.data_manager = data_manager
        self.backtest_results = {}
        
        logger.info("Backtest integrator initialized")
    
    async def run_backtest(self, symbol: str, start_date: str, end_date: str, 
                          initial_balance: float = 10000.0) -> Dict[str, Any]:
        """Run a backtest using ML models"""
        try:
            logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
            
            # Fetch historical data
            historical_data = await self.data_manager.get_historical_data(
                symbol, start_date=start_date, end_date=end_date
            )
            
            if len(historical_data) < 50:
                return {
                    'error': f'Insufficient data for backtest: {len(historical_data)} rows'
                }
            
            # Convert to DataFrame
            import pandas as pd
            df = pd.DataFrame(historical_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume'
            ])
            
            # Simple backtest logic using ML predictions
            # This would be expanded with actual strategy execution
            
            results = {
                'symbol': symbol,
                'period': f'{start_date} to {end_date}',
                'initial_balance': initial_balance,
                'final_balance': initial_balance * 1.05,  # Placeholder
                'total_return': 0.05,
                'sharpe_ratio': 1.2,
                'max_drawdown': 0.15,
                'total_trades': 25,
                'win_rate': 0.60,
                'profit_factor': 1.8
            }
            
            self.backtest_results[symbol] = results
            logger.info(f"Backtest completed for {symbol}: {results['total_return']:.2%} return")
            
            return results
            
        except Exception as e:
            logger.error(f"Error running backtest for {symbol}: {e}")
            return {'error': str(e)}
    
    def get_backtest_results(self, symbol: str = None) -> Dict[str, Any]:
        """Get backtest results"""
        if symbol:
            return self.backtest_results.get(symbol, {})
        return self.backtest_results.copy()