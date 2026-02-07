import os

import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any
import yfinance as yf


from local_agents.quant_agent_vlm.src.trading_graph import TradingGraph
from data_processing.data_provider.mairui import Mairui


class WebTradingAnalyzer:
    def __init__(self, mcp_tools):
        """Initialize the web trading analyzer."""
        self.trading_graph = TradingGraph()
        # Set data_dir to quant_agent_vlm/data directory
        # Get the directory where this file is located (src/)
        # Then go up one level to quant_agent_vlm/
        current_file_path = Path(__file__).resolve()
        quant_agent_vlm_dir = current_file_path.parent.parent
        self.data_dir = quant_agent_vlm_dir / "data"

        self.debug = True
        self.mcp_tools = mcp_tools

        # Ensure data dir exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Available assets and their display names
        self.asset_mapping = {
            'SPX': 'S&P 500',
            'BTC': 'Bitcoin',
            'GC': 'Gold Futures',
            'NQ': 'Nasdaq Futures',
            'CL': 'Crude Oil',
            'ES': 'E-mini S&P 500',
            'DJI': 'Dow Jones',
            'QQQ': 'Invesco QQQ Trust',
            'VIX': 'Volatility Index',
            'DXY': 'US Dollar Index',
            'AAPL': 'Apple Inc.',  # New asset
            'TSLA': 'Tesla Inc.',  # New asset
        }

        # Yahoo Finance symbol mapping
        self.yfinance_symbols = {
            'SPX': '^GSPC',  # S&P 500
            'BTC': 'BTC-USD',  # Bitcoin
            'GC': 'GC=F',  # Gold Futures
            'NQ': 'NQ=F',  # Nasdaq Futures
            'CL': 'CL=F',  # Crude Oil
            'ES': 'ES=F',  # E-mini S&P 500
            'DJI': '^DJI',  # Dow Jones
            'QQQ': 'QQQ',  # Invesco QQQ Trust
            'VIX': '^VIX',  # Volatility Index
            'DXY': 'DX-Y.NYB',  # US Dollar Index
        }

        # Available timeframes
        self.timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']

        # Yahoo Finance interval mapping
        self.yfinance_intervals = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '4h',  # yfinance supports 4h natively!
            '1d': '1d'
        }

        # Load persisted custom assets
        self.custom_assets_file = self.data_dir / "custom_assets.json"
        self.custom_assets = self.load_custom_assets()

    def fetch_yfinance_data(self, symbol: str, interval: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch OHLCV data from Yahoo Finance."""
        try:
            yf_symbol = self.yfinance_symbols.get(symbol, symbol)
            yf_interval = self.yfinance_intervals.get(interval, interval)

            df = yf.download(tickers=yf_symbol, start=start_date, end=end_date, interval=yf_interval)

            if df is None or df.empty:
                return pd.DataFrame()

            # Ensure df is a DataFrame, not a Series
            if isinstance(df, pd.Series):
                df = df.to_frame()

            # Reset index to ensure we have a clean DataFrame
            df = df.reset_index()

            # Ensure we have a DataFrame
            if not isinstance(df, pd.DataFrame):
                return pd.DataFrame()

            # Handle potential MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Rename columns if needed
            column_mapping = {
                'Date': 'Datetime',
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            }

            # Only rename columns that exist
            existing_columns = {old: new for old, new in column_mapping.items() if old in df.columns}
            df = df.rename(columns=existing_columns)

            # Ensure we have the required columns
            required_columns = ["Datetime", "Open", "High", "Low", "Close"]
            if not all(col in df.columns for col in required_columns):
                print(f"Warning: Missing columns. Available: {list(df.columns)}")
                return pd.DataFrame()

            # Select only the required columns
            df = df[required_columns]
            df['Datetime'] = pd.to_datetime(df['Datetime'])

            return df

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_yfinance_data_with_datetime(self, symbol: str, interval: str, start_datetime: datetime,
                                          end_datetime: datetime) -> pd.DataFrame:
        """Fetch OHLCV data from Yahoo Finance using datetime objects for exact time precision."""
        try:
            yf_symbol = self.yfinance_symbols.get(symbol, symbol)
            yf_interval = self.yfinance_intervals.get(interval, interval)

            print(f"Fetching {yf_symbol} from {start_datetime} to {end_datetime} with interval {yf_interval}")

            # Use datetime objects directly for yfinance
            df = yf.download(
                tickers=yf_symbol,
                start=start_datetime,
                end=end_datetime,
                interval=yf_interval,
                auto_adjust=True,
                prepost=False
            )

            if df is None or df.empty:
                print(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Ensure df is a DataFrame, not a Series
            if isinstance(df, pd.Series):
                df = df.to_frame()

            # Reset index to ensure we have a clean DataFrame
            df = df.reset_index()

            # Ensure we have a DataFrame
            if not isinstance(df, pd.DataFrame):
                return pd.DataFrame()

            # Handle potential MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Rename columns if needed
            column_mapping = {
                'Date': 'Datetime',
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            }

            # Only rename columns that exist
            existing_columns = {old: new for old, new in column_mapping.items() if old in df.columns}
            df = df.rename(columns=existing_columns)

            # Ensure we have the required columns
            required_columns = ["Datetime", "Open", "High", "Low", "Close"]
            if not all(col in df.columns for col in required_columns):
                print(f"Warning: Missing columns. Available: {list(df.columns)}")
                return pd.DataFrame()

            # Select only the required columns
            df = df[required_columns]
            df['Datetime'] = pd.to_datetime(df['Datetime'])

            print(f"Successfully fetched {len(df)} data points for {symbol}")
            print(f"Date range: {df['Datetime'].min()} to {df['Datetime'].max()}")

            return df

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_my_data_with_date(self, symbol: str, start_date: str,
                                          end_date: str, interval: str = '60m') -> pd.DataFrame:
        """Fetch OHLCV data from Yahoo Finance using datetime objects for exact time precision."""
        try:
            print(f"Fetching {symbol} from {start_date} to {end_date} with interval {interval}")
            mydata = Mairui()
            results = mydata.get_stock_history(symbol, start_date, end_date, '60')
            df = pd.DataFrame(results)

            if df is None or df.empty:
                print(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Rename columns if needed
            column_mapping = {
                't': 'Datetime',
                'o': 'Open',
                'h': 'High',
                'l': 'Low',
                'c': 'Close',
                'v': 'Volume'
            }

            # Only rename columns that exist
            existing_columns = {old: new for old, new in column_mapping.items() if old in df.columns}
            df = df.rename(columns=existing_columns)

            # Ensure we have the required columns
            required_columns = ["Datetime", "Open", "High", "Low", "Close"]
            if not all(col in df.columns for col in required_columns):
                print(f"Warning: Missing columns. Available: {list(df.columns)}")
                return pd.DataFrame()

            # Select only the required columns
            df = df[required_columns]
            df['Datetime'] = pd.to_datetime(df['Datetime'])

            print(f"Successfully fetched {len(df)} data points for {symbol}")
            print(f"Date range: {df['Datetime'].min()} to {df['Datetime'].max()}")

            return df

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def get_available_assets(self) -> list:
        """Get list of available assets from the asset mapping dictionary."""
        return sorted(list(self.asset_mapping.keys()))

    def get_available_files(self, asset: str, timeframe: str) -> list:
        """Get available data files for a specific asset and timeframe."""
        asset_dir = self.data_dir / asset.lower()
        if not asset_dir.exists():
            return []

        pattern = f"{asset}_{timeframe}_*.csv"
        files = list(asset_dir.glob(pattern))
        return sorted(files)

    async def run_analysis(self, df: pd.DataFrame, asset_name: str, timeframe: str) -> Dict[str, Any]:
        """Run the trading analysis on the provided DataFrame."""
        try:
            # Debug: Check DataFrame structure
            print(f"DataFrame columns: {df.columns}")
            print(f"DataFrame index: {type(df.index)}")
            print(f"DataFrame shape: {df.shape}")

            # Prepare data for analysis
            if len(df) > 49:
                df_slice = df.tail(49).iloc[:-3]
            else:
                df_slice = df.tail(45)

            # Ensure DataFrame has the expected structure
            required_columns = ["Datetime", "Open", "High", "Low", "Close"]
            if not all(col in df_slice.columns for col in required_columns):
                return {
                    "success": False,
                    "error": f"Missing required columns. Available: {list(df_slice.columns)}"
                }

            # Reset index to avoid any MultiIndex issues
            df_slice = df_slice.reset_index(drop=True)

            # Debug: Check the slice before conversion
            print(f"Slice columns: {df_slice.columns}")
            print(f"Slice index: {type(df_slice.index)}")

            # Convert to dict for tool input - use explicit conversion to avoid tuple keys
            df_slice_dict = {}
            for col in required_columns:
                if col == 'Datetime':
                    # Convert datetime objects to strings for JSON serialization
                    df_slice_dict[col] = df_slice[col].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
                else:
                    df_slice_dict[col] = df_slice[col].tolist()

            # Debug: Check the resulting dictionary
            print(f"Dictionary keys: {list(df_slice_dict.keys())}")
            print(f"Dictionary key types: {[type(k) for k in df_slice_dict.keys()]}")

            # Format timeframe for display
            display_timeframe = timeframe
            if timeframe.endswith('h'):
                display_timeframe += 'our'
            elif timeframe.endswith('m'):
                display_timeframe += 'in'
            elif timeframe.endswith('d'):
                display_timeframe += 'ay'
            else:
                display_timeframe += 'min'

            # Create initial state
            initial_state = {
                "kline_data": df_slice_dict,
                "analysis_results": None,
                "messages": [],
                "time_frame": display_timeframe,
                "stock_name": asset_name
            }

            self.trading_graph.set_graph_with_tools(self.mcp_tools)

            # Run the trading graph with dynamic tools
            final_state = await self.trading_graph.graph.ainvoke(initial_state)

            return {
                "success": True,
                "final_state": final_state,
                "asset_name": asset_name,
                "timeframe": display_timeframe,
                "data_length": len(df_slice)
            }

        except Exception as e:
            error_msg = str(e)

            # Check for specific API key authentication errors
            if "authentication" in error_msg.lower() or "invalid api key" in error_msg.lower() or "401" in error_msg:
                return {
                    "success": False,
                    "error": "❌ Invalid API Key: The OpenAI API key you provided is invalid or has expired. Please check your API key in the Settings section and try again."
                }
            elif "rate limit" in error_msg.lower() or "429" in error_msg:
                return {
                    "success": False,
                    "error": "⚠️ Rate Limit Exceeded: You've hit the OpenAI API rate limit. Please wait a moment and try again."
                }
            elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
                return {
                    "success": False,
                    "error": "💳 Billing Issue: Your OpenAI account has insufficient credits or billing issues. Please check your OpenAI account."
                }
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                return {
                    "success": False,
                    "error": "🌐 Network Error: Unable to connect to OpenAI servers. Please check your internet connection and try again."
                }
            else:
                return {
                    "success": False,
                    "error": f"❌ Analysis Error: {error_msg}"
                }

    def extract_analysis_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and format analysis results for web display."""
        if not results["success"]:
            return {"error": results["error"]}

        final_state = results["final_state"]

        # Extract analysis results from state fields
        technical_indicators = final_state.get("indicator_report", "")
        pattern_analysis = final_state.get("pattern_report", "")
        trend_analysis = final_state.get("trend_report", "")
        final_decision_raw = final_state.get("final_trade_decision", "")

        # Extract chart data if available
        pattern_chart = final_state.get("pattern_image", "")
        trend_chart = final_state.get("trend_image", "")
        pattern_image_filename = final_state.get("pattern_image_filename", "")
        trend_image_filename = final_state.get("trend_image_filename", "")

        # Parse final decision
        final_decision = ""
        if final_decision_raw:
            try:
                # Try to extract JSON from the decision
                start = final_decision_raw.find('{')
                end = final_decision_raw.rfind('}') + 1
                if start != -1 and end != 0:
                    json_str = final_decision_raw[start:end]
                    decision_data = json.loads(json_str)
                    final_decision = {
                        "decision": decision_data.get('decision', 'N/A'),
                        "risk_reward_ratio": decision_data.get('risk_reward_ratio', 'N/A'),
                        "forecast_horizon": decision_data.get('forecast_horizon', 'N/A'),
                        "justification": decision_data.get('justification', 'N/A')
                    }
                else:
                    # If no JSON found, return the raw text
                    final_decision = {"raw": final_decision_raw}
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw text
                final_decision = {"raw": final_decision_raw}

        return {
            "success": True,
            "asset_name": results["asset_name"],
            "timeframe": results["timeframe"],
            "data_length": results["data_length"],
            "technical_indicators": technical_indicators,
            "pattern_analysis": pattern_analysis,
            "trend_analysis": trend_analysis,
            "pattern_chart": pattern_chart,
            "trend_chart": trend_chart,
            "pattern_image_filename": pattern_image_filename,
            "trend_image_filename": trend_image_filename,
            "final_decision": final_decision
        }

    def get_timeframe_date_limits(self, timeframe: str) -> Dict[str, Any]:
        """Get valid date range limits for a given timeframe."""
        limits = {
            "1m": {"max_days": 7, "description": "1 minute data: max 7 days"},
            "2m": {"max_days": 60, "description": "2 minute data: max 60 days"},
            "5m": {"max_days": 60, "description": "5 minute data: max 60 days"},
            "15m": {"max_days": 60, "description": "15 minute data: max 60 days"},
            "30m": {"max_days": 60, "description": "30 minute data: max 60 days"},
            "60m": {"max_days": 730, "description": "1 hour data: max 730 days"},
            "90m": {"max_days": 60, "description": "90 minute data: max 60 days"},
            "1h": {"max_days": 730, "description": "1 hour data: max 730 days"},
            "4h": {"max_days": 730, "description": "4 hour data: max 730 days"},
            "1d": {"max_days": 730, "description": "1 day data: max 730 days"},
            "5d": {"max_days": 60, "description": "5 day data: max 60 days"},
            "1wk": {"max_days": 730, "description": "1 week data: max 730 days"},
            "1mo": {"max_days": 730, "description": "1 month data: max 730 days"},
            "3mo": {"max_days": 730, "description": "3 month data: max 730 days"}
        }

        return limits.get(timeframe, {"max_days": 730, "description": "Default: max 730 days"})

    def validate_date_range(self, start_date: str, end_date: str, timeframe: str,
                            start_time: str = "00:00", end_time: str = "23:59") -> Dict[str, Any]:
        """Validate date and time range for the given timeframe."""
        try:
            # Create datetime objects with time
            start_datetime_str = f"{start_date} {start_time}"
            end_datetime_str = f"{end_date} {end_time}"

            start = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M')
            end = datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M')

            if start >= end:
                return {"valid": False, "error": "Start date/time must be before end date/time"}

            # Get timeframe limits
            limits = self.get_timeframe_date_limits(timeframe)
            max_days = limits["max_days"]

            # Calculate time difference in days (including fractional days)
            time_diff = end - start
            days_diff = time_diff.total_seconds() / (24 * 3600)  # Convert to days

            if days_diff > max_days:
                return {
                    "valid": False,
                    "error": f"Time range too large. {limits['description']}. Please select a smaller range.",
                    "max_days": max_days,
                    "current_days": round(days_diff, 2)
                }

            return {"valid": True, "days": round(days_diff, 2)}

        except ValueError as e:
            return {"valid": False, "error": f"Invalid date/time format: {str(e)}"}

    def validate_api_key(self) -> Dict[str, Any]:
        """Validate the current API key by making a simple test call."""
        try:
            from openai import OpenAI
            client = OpenAI()

            # Make a simple test call
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )

            return {"valid": True, "message": "API key is valid"}

        except Exception as e:
            error_msg = str(e)

            if "authentication" in error_msg.lower() or "invalid api key" in error_msg.lower() or "401" in error_msg:
                return {
                    "valid": False,
                    "error": "❌ Invalid API Key: The OpenAI API key is invalid or has expired. Please update it in the Settings section."
                }
            elif "rate limit" in error_msg.lower() or "429" in error_msg:
                return {
                    "valid": False,
                    "error": "⚠️ Rate Limit Exceeded: You've hit the OpenAI API rate limit. Please wait a moment and try again."
                }
            elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
                return {
                    "valid": False,
                    "error": "💳 Billing Issue: Your OpenAI account has insufficient credits or billing issues. Please check your OpenAI account."
                }
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                return {
                    "valid": False,
                    "error": "🌐 Network Error: Unable to connect to OpenAI servers. Please check your internet connection."
                }
            else:
                return {
                    "valid": False,
                    "error": f"❌ API Key Error: {error_msg}"
                }

    def load_custom_assets(self) -> list:
        """Load custom assets from persistent JSON file."""
        try:
            if self.custom_assets_file.exists():
                with open(self.custom_assets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            return []
        except Exception as e:
            print(f"Error loading custom assets: {e}")
            return []

    def save_custom_asset(self, symbol: str) -> bool:
        """Save a custom asset symbol persistently (avoid duplicates)."""
        try:
            symbol = symbol.strip()
            if not symbol:
                return False
            if symbol in self.custom_assets:
                return True  # already present
            self.custom_assets.append(symbol)
            # write to file
            with open(self.custom_assets_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_assets, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving custom asset '{symbol}': {e}")
            return False