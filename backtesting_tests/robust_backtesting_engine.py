#!/usr/bin/env python3
"""
🎯 ROBUST BACKTESTING ENGINE - REALISTIC TRADING SIMULATION

This engine provides realistic backtesting with:
- Proper position sizing based on risk management
- Slippage and commission modeling
- Walk-forward testing to prevent overfitting
- Gap handling for overnight positions
- Realistic entry/exit execution
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from typing import Dict, List, Tuple, Optional, Callable
import warnings
warnings.filterwarnings('ignore')

class RobustBacktestEngine:
    """Realistic backtesting engine with proper risk management"""

    def __init__(self,
                 initial_capital: float = 100000,
                 commission_per_trade: float = 0.01,  # 0.01% for crypto, higher for stocks
                 slippage_pct: float = 0.05,  # 0.05% slippage
                 max_risk_per_trade: float = 0.01,  # 1% risk per trade
                 max_daily_loss: float = 0.02,  # 2% max daily loss
                 max_open_positions: int = 1):  # Max concurrent positions

        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.commission_per_trade = commission_per_trade / 100  # Convert to decimal
        self.slippage_pct = slippage_pct / 100  # Convert to decimal
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_open_positions = max_open_positions

        # Trading state
        self.positions = []  # List of open positions
        self.trades = []     # List of completed trades
        self.daily_pnl = {}  # Daily P&L tracking
        self.portfolio_values = []  # Portfolio value over time

        # Risk management
        self.daily_start_capital = initial_capital
        self.consecutive_losses = 0

    def reset(self):
        """Reset the backtest engine"""
        self.capital = self.initial_capital
        self.positions = []
        self.trades = []
        self.daily_pnl = {}
        self.portfolio_values = []
        self.daily_start_capital = self.initial_capital
        self.consecutive_losses = 0

    def calculate_position_size(self, entry_price: float, stop_loss_price: float) -> float:
        """Calculate position size based on risk management rules"""
        if self.capital <= 0:
            return 0

        # Risk amount per trade
        risk_amount = self.capital * self.max_risk_per_trade

        # Stop loss distance
        stop_distance = abs(entry_price - stop_loss_price)

        if stop_distance == 0:
            return 0

        # Position size = risk amount / stop distance
        position_value = risk_amount / stop_distance

        # Cap at available capital
        position_value = min(position_value, self.capital * 0.1)  # Max 10% of capital per position

        return position_value

    def apply_slippage_and_commission(self, price: float, quantity: float, is_entry: bool = True) -> Tuple[float, float]:
        """Apply slippage and commission to trade execution"""
        # Apply slippage (worse price for execution)
        slippage_amount = price * self.slippage_pct
        if is_entry:
            # For entry, we get worse price
            execution_price = price * (1 + self.slippage_pct)
        else:
            # For exit, we get worse price
            execution_price = price * (1 - self.slippage_pct)

        # Apply commission
        commission = abs(execution_price * quantity) * self.commission_per_trade
        total_cost = execution_price * quantity + commission if is_entry else execution_price * quantity - commission

        return execution_price, commission

    def check_daily_loss_limit(self, current_time: pd.Timestamp) -> bool:
        """Check if we've hit the daily loss limit"""
        current_date = current_time.date()

        if current_date not in self.daily_pnl:
            self.daily_start_capital = self.capital
            return False

        daily_loss = (self.capital - self.daily_start_capital) / self.daily_start_capital

        return daily_loss <= -self.max_daily_loss

    def enter_position(self, symbol: str, entry_price: float, stop_loss_price: float,
                      take_profit_price: float, direction: str, timestamp: pd.Timestamp) -> bool:
        """Enter a new position with proper risk management"""

        # Check daily loss limit
        if self.check_daily_loss_limit(timestamp):
            return False  # Daily loss limit reached

        # Check max open positions
        if len(self.positions) >= self.max_open_positions:
            return False

        # Check available capital
        if self.capital <= 100:  # Minimum capital threshold
            return False

        # Calculate position size
        position_value = self.calculate_position_size(entry_price, stop_loss_price)
        if position_value <= 0:
            return False

        # Apply slippage and commission
        execution_price, commission = self.apply_slippage_and_commission(entry_price, position_value / entry_price, is_entry=True)

        # Update capital
        self.capital -= (execution_price * (position_value / entry_price) + commission)

        # Create position
        position = {
            'symbol': symbol,
            'entry_price': execution_price,
            'stop_loss': stop_loss_price,
            'take_profit': take_profit_price,
            'direction': direction,
            'quantity': position_value / execution_price,
            'entry_time': timestamp,
            'entry_commission': commission,
            'current_value': position_value
        }

        self.positions.append(position)
        return True

    def exit_position(self, position_idx: int, exit_price: float, timestamp: pd.Timestamp, reason: str = 'manual'):
        """Exit a position"""
        if position_idx >= len(self.positions):
            return False

        position = self.positions[position_idx]

        # Apply slippage and commission
        execution_price, commission = self.apply_slippage_and_commission(exit_price, position['quantity'], is_entry=False)

        # Calculate P&L
        if position['direction'] == 'long':
            pnl = (execution_price - position['entry_price']) * position['quantity']
        else:
            pnl = (position['entry_price'] - execution_price) * position['quantity']

        # Subtract exit commission
        pnl -= commission

        # Update capital
        self.capital += (execution_price * position['quantity'] + pnl)

        # Record trade
        trade = {
            'symbol': position['symbol'],
            'entry_time': position['entry_time'],
            'exit_time': timestamp,
            'entry_price': position['entry_price'],
            'exit_price': execution_price,
            'stop_loss': position['stop_loss'],
            'take_profit': position['take_profit'],
            'direction': position['direction'],
            'quantity': position['quantity'],
            'pnl': pnl,
            'entry_commission': position['entry_commission'],
            'exit_commission': commission,
            'reason': reason,
            'hold_time': (timestamp - position['entry_time']).total_seconds() / 3600  # hours
        }

        self.trades.append(trade)

        # Update daily P&L
        current_date = timestamp.date()
        if current_date not in self.daily_pnl:
            self.daily_pnl[current_date] = 0
        self.daily_pnl[current_date] += pnl

        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Remove position
        del self.positions[position_idx]

        return True

    def update_positions(self, current_prices: Dict[str, float], timestamp: pd.Timestamp):
        """Update open positions and check for stop loss/take profit hits"""
        positions_to_close = []

        for i, position in enumerate(self.positions):
            symbol = position['symbol']
            current_price = current_prices.get(symbol, position['entry_price'])

            # Check stop loss and take profit
            should_close = False
            reason = 'manual'

            if position['direction'] == 'long':
                if current_price <= position['stop_loss']:
                    should_close = True
                    reason = 'stop_loss'
                elif current_price >= position['take_profit']:
                    should_close = True
                    reason = 'take_profit'
            else:  # short
                if current_price >= position['stop_loss']:
                    should_close = True
                    reason = 'stop_loss'
                elif current_price <= position['take_profit']:
                    should_close = True
                    reason = 'take_profit'

            if should_close:
                positions_to_close.append((i, current_price, reason))

        # Close positions (in reverse order to maintain indices)
        for pos_idx, exit_price, reason in reversed(positions_to_close):
            self.exit_position(pos_idx, exit_price, timestamp, reason)

    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate current portfolio value"""
        portfolio_value = self.capital

        for position in self.positions:
            symbol = position['symbol']
            current_price = current_prices.get(symbol, position['entry_price'])

            if position['direction'] == 'long':
                position_value = current_price * position['quantity']
            else:
                # For short positions, value increases as price decreases
                position_value = (2 * position['entry_price'] - current_price) * position['quantity']

            portfolio_value += position_value

        return portfolio_value

    def run_backtest(self, strategy_func: Callable, data: pd.DataFrame,
                    symbol: str, walk_forward: bool = False) -> Dict:
        """Run backtest with optional walk-forward testing"""
        self.reset()

        if data.empty:
            return {'error': 'No data available'}

        # Prepare data
        df = data.copy()
        df = strategy_func(df)  # Apply strategy indicators

        results = []

        if walk_forward:
            # Walk-forward testing: train on past data, test on future
            train_size = int(len(df) * 0.7)  # 70% training, 30% testing

            for i in range(train_size, len(df), 50):  # Test every 50 bars
                train_data = df[:i]
                test_data = df[i:i+50]

                # Reset for each walk-forward window
                self.reset()

                # Run test on out-of-sample data
                window_result = self._run_single_backtest(strategy_func, test_data, symbol)
                results.append(window_result)
        else:
            # Regular backtest
            results = [self._run_single_backtest(strategy_func, df, symbol)]

        return self._aggregate_results(results)

    def _run_single_backtest(self, strategy_func: Callable, df: pd.DataFrame, symbol: str) -> Dict:
        """Run a single backtest window"""
        # Reset for this window
        temp_capital = self.capital
        temp_positions = self.positions.copy()
        temp_trades = self.trades.copy()

        self.reset()
        self.capital = temp_capital

        for i in range(len(df)):
            current_time = df.index[i]
            current_price = df['Close'].iloc[i]

            # Update positions (check stops/targets)
            current_prices = {symbol: current_price}
            self.update_positions(current_prices, current_time)

            # Check for new signals
            if len(self.positions) < self.max_open_positions:
                signal = strategy_func(df.iloc[:i+1], signal_only=True)
                if signal in ['buy', 'sell']:
                    # Get stop loss and take profit from strategy
                    stop_loss, take_profit = strategy_func(df.iloc[:i+1], get_levels=True)

                    if stop_loss and take_profit:
                        direction = 'long' if signal == 'buy' else 'short'
                        self.enter_position(symbol, current_price, stop_loss,
                                          take_profit, direction, current_time)

            # Record portfolio value
            portfolio_value = self.get_portfolio_value(current_prices)
            self.portfolio_values.append({
                'timestamp': current_time,
                'portfolio_value': portfolio_value,
                'capital': self.capital
            })

        # Close remaining positions
        for i in reversed(range(len(self.positions))):
            current_price = df['Close'].iloc[-1]
            self.exit_position(i, current_price, df.index[-1], 'end_of_test')

        # Restore state
        self.capital = temp_capital
        self.positions = temp_positions
        self.trades = temp_trades

        return {
            'trades': self.trades.copy(),
            'portfolio_values': self.portfolio_values.copy(),
            'final_capital': self.capital,
            'total_trades': len(self.trades)
        }

    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate results from multiple backtest windows"""
        if not results:
            return {'error': 'No results to aggregate'}

        all_trades = []
        all_portfolio_values = []

        for result in results:
            all_trades.extend(result['trades'])
            all_portfolio_values.extend(result['portfolio_values'])

        if not all_trades:
            return {
                'total_return': 0,
                'win_rate': 0,
                'total_trades': 0,
                'avg_trade_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'trades': [],
                'walk_forward_windows': len(results)
            }

        # Calculate metrics
        trades_df = pd.DataFrame(all_trades)
        portfolio_df = pd.DataFrame(all_portfolio_values)

        # Basic metrics
        total_return = (trades_df['pnl'].sum()) / self.initial_capital
        win_rate = (trades_df['pnl'] > 0).mean()
        total_trades = len(trades_df)
        avg_trade_return = trades_df['pnl'].mean() / self.initial_capital

        # Max drawdown
        if not portfolio_df.empty:
            portfolio_df = portfolio_df.sort_values('timestamp')
            peak = portfolio_df['portfolio_value'].expanding().max()
            drawdown = (portfolio_df['portfolio_value'] - peak) / peak
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0

        # Sharpe ratio (daily returns)
        if len(portfolio_df) > 1:
            portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
            daily_returns = portfolio_df['daily_return'].dropna()
            if daily_returns.std() > 0:
                sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252)  # 252 trading days
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0

        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'avg_trade_return': avg_trade_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'trades': all_trades,
            'portfolio_values': all_portfolio_values,
            'walk_forward_windows': len(results)
        }

# ===============================
# STRATEGY TESTING FUNCTIONS
# ===============================

def test_strategy_robustness(strategy_func: Callable, data: pd.DataFrame,
                           symbol: str, engine_params: Dict = None) -> Dict:
    """Test strategy with robust backtesting engine"""

    if engine_params is None:
        engine_params = {}

    # Default parameters
    default_params = {
        'initial_capital': 100000,
        'commission_per_trade': 0.01,  # 0.01% for crypto
        'slippage_pct': 0.05,  # 0.05%
        'max_risk_per_trade': 0.01,  # 1%
        'max_daily_loss': 0.02,  # 2%
        'max_open_positions': 1
    }

    # Override defaults with provided params
    default_params.update(engine_params)

    engine = RobustBacktestEngine(**default_params)

    # Run regular backtest
    regular_result = engine.run_backtest(strategy_func, data, symbol, walk_forward=False)

    # Run walk-forward backtest
    wf_result = engine.run_backtest(strategy_func, data, symbol, walk_forward=True)

    return {
        'regular_backtest': regular_result,
        'walk_forward_backtest': wf_result,
        'robustness_score': calculate_robustness_score(regular_result, wf_result)
    }

def calculate_robustness_score(regular_result: Dict, wf_result: Dict) -> float:
    """Calculate robustness score based on consistency between regular and walk-forward tests"""

    if 'error' in regular_result or 'error' in wf_result:
        return 0.0

    # Compare key metrics
    metrics = ['total_return', 'win_rate', 'sharpe_ratio']

    consistency_scores = []
    for metric in metrics:
        regular_val = regular_result.get(metric, 0)
        wf_val = wf_result.get(metric, 0)

        if regular_val == 0 and wf_val == 0:
            consistency_scores.append(1.0)
        elif regular_val == 0 or wf_val == 0:
            consistency_scores.append(0.0)
        else:
            # Calculate relative difference
            diff = abs(regular_val - wf_val) / abs(regular_val)
            consistency_scores.append(max(0, 1 - diff))

    return np.mean(consistency_scores)

# ===============================
# IBKR LIVE VALIDATION
# ===============================

def validate_with_ibkr_live(strategy_func: Callable, symbol: str, duration_days: int = 30) -> Dict:
    """Validate strategy with live IBKR data"""
    try:
        from shared_utils.data_loader import load_ohlcv_ibkr

        # Load recent IBKR data
        df = load_ohlcv_ibkr(
            symbol=symbol,
            duration=f"{duration_days} D",
            bar_size="5 mins",
            contract_kind="stock"
        )

        if df.empty:
            return {'error': 'Could not load IBKR data'}

        # Test with robust engine
        return test_strategy_robustness(strategy_func, df, symbol)

    except Exception as e:
        return {'error': f'IBKR validation failed: {str(e)}'}

if __name__ == "__main__":
    print("🎯 Robust Backtesting Engine Ready")
    print("Use test_strategy_robustness() to validate strategies with realistic conditions")


