import multiprocessing
from datetime import datetime
import asyncio
import pandas as pd
from importlib import import_module
from functools import lru_cache
import logging

from db.mysql.db_schemas import Simulator, AgentTrading, Rule, RulePool, PoolStock
from end_points.common.const.consts import Trade
from end_points.get_simulator.operations.get_simulator_utils import update_sim_model

logger = logging.getLogger(__name__)


@lru_cache(maxsize=100)
def get_agent_func(full_path: str):
    """
    Dynamically import agent function from module path.

    Args:
        full_path: Python path in format "module.path" or "module.path.function_name"
                   Examples:
                   - "local_agents.fingenius.main" (will look for 'main' function)
                   - "local_agents.fingenius.main.fingenius_main" (will look for 'fingenius_main' function)

    Returns:
        The agent function, or None if import fails
    """
    try:
        # Split by dots
        parts = full_path.split('.')

        # If there are more than 2 parts, the last part might be the function name
        # Try to detect if the last part is a function name (heuristic: module doesn't exist)
        if len(parts) > 2:
            # Try importing as if last part is a function
            module_path = '.'.join(parts[:-1])
            func_name = parts[-1]

            try:
                module = import_module(module_path)
                func = getattr(module, func_name)
                if callable(func):
                    logger.info(f"Successfully imported {func_name} from {module_path}")
                    return func
            except (ImportError, AttributeError):
                # Fall through to try importing as a module
                pass

        # Default: import as module and look for 'main' function
        module = import_module(full_path)
        return getattr(module, 'main')

    except Exception as e:
        logger.error(f"Failed to import agent from {full_path}: {e}")
        return None


def get_agent_buying_stocks(db, rule_id):
    """
    Get all stocks from pools that belong to this rule.

    Args:
        db: Database session
        rule_id: Rule ID

    Returns:
        List of stock codes (strings) without exchange suffix
    """
    # Get distinct pool_ids for this rule_id
    pool_ids = db.session.query(RulePool.pool_id)\
        .filter(RulePool.rule_id == rule_id)\
        .distinct()\
        .all()

    pool_ids = [p[0] for p in pool_ids if p[0]]

    if not pool_ids:
        return []

    # Get all stock codes for these pool_ids
    stocks = db.session.query(PoolStock.stock_code)\
        .filter(PoolStock.pool_id.in_(pool_ids))\
        .distinct()\
        .all()

    # Strip exchange suffix (e.g., '000001.SZ' -> '000001')
    stock_list = [s.split('.')[0] if '.' in s else s for (s,) in stocks]
    return stock_list

def update_rule_trading(db, rule_id, trade_type, stock_code, trade_date):
    """
    Update trading record for a rule/stock/date.
    Uses merge() to handle concurrent updates safely.
    """
    from sqlalchemy import exc
    from sqlalchemy.orm.attributes import flag_modified

    # Strip stock exchange suffix before storing in database
    stock_code = stock_code.split('.')[0] if '.' in stock_code else stock_code

    # First try to get existing record
    existing_record = db.session.query(AgentTrading)\
        .filter(AgentTrading.rule_id == rule_id)\
        .filter(AgentTrading.stock == stock_code)\
        .filter(AgentTrading.trading_date == trade_date)\
        .with_for_update()\
        .first()

    if existing_record:
        # Update existing record and explicitly mark as modified
        existing_record.trading_type = trade_type
        flag_modified(existing_record, 'trading_type')
    else:
        # Insert new record (will fail if concurrent insert happened)
        new_record = AgentTrading(
            rule_id=rule_id,
            trading_type=trade_type,
            stock=stock_code,
            trading_date=trade_date,
        )
        db.session.add(new_record)

    try:
        db.session.commit()
    except exc.IntegrityError:
        # Handle concurrent insert: retry by getting and updating
        db.session.rollback()
        existing_record = db.session.query(AgentTrading)\
            .filter(AgentTrading.rule_id == rule_id)\
            .filter(AgentTrading.stock == stock_code)\
            .filter(AgentTrading.trading_date == trade_date)\
            .first()
        if existing_record:
            existing_record.trading_type = trade_type
            flag_modified(existing_record, 'trading_type')
            db.session.commit()
        else:
            # Should not happen, but fallback to insert
            new_record = AgentTrading(
                rule_id=rule_id,
                trading_type=trade_type,
                stock=stock_code,
                trading_date=trade_date,
            )
            db.session.add(new_record)
            db.session.commit()
    return

def run_sim_agent(db, agent_sim_id):
    agent_rule_id = db.session.query(Simulator.rule_id).filter(Simulator.id == agent_sim_id).scalar()
    record = db.session.query(AgentTrading).filter(AgentTrading.rule_id == agent_rule_id).all()
    indicating_items = []
    for each_item in record:
        stock_code = each_item.stock
        indicating_date = pd.Timestamp(each_item.trading_date)
        indi_item = {
            'stock_code': stock_code,
            'indicating_date': indicating_date,
        }
        indicating_items.append(indi_item)

    indicating_date = update_sim_model(db, agent_sim_id, indicating_items)
    return indicating_date


def run_async(coro):
    """
    Helper function to run async code in a separate thread to avoid
    conflicts with existing event loops (e.g., in FastAPI).
    """
    import concurrent.futures
    import threading

    def run_in_thread():
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        return future.result()


def run_agent_for_stock(db, rule_id, stock_code):
    """
    Run an agent-type rule for a single stock.

    Args:
        db: Database session
        rule_id: Agent rule ID (3000=fingenius, 3001=tauric, 3002=quant_agent_vlm)
        stock_code: Stock code to analyze

    Returns:
        dict: {
            'success': bool,
            'stock_code': str,
            'indicating': str,
            'result': bool,
            'error': str (if failed)
        }
    """
    indicating_date = datetime.now().date()
    print(f'Start running agent {rule_id} for {stock_code}...')

    # Get rule information to check type
    rule_record = db.session.query(Rule).filter(Rule.id == rule_id).first()
    if not rule_record:
        return {
            'success': False,
            'stock_code': stock_code,
            'error': f'Rule {rule_id} not found'
        }

    rule_type = rule_record.type

    # Handle remote agent
    if rule_type == 'remote_agent':
        base_url = rule_record.info  # Get base_url from info column
        if not base_url:
            return {
                'success': False,
                'stock_code': stock_code,
                'error': 'Remote agent must have a base_url in info field'
            }

        try:
            from remote_agents_a2a.trading_agent_client import run_trading_agent_client

            # Strip stock exchange suffix (e.g., '600519.SH' -> '600519')
            clean_stock_code = stock_code.split('.')[0] if '.' in stock_code else stock_code
            # Run the remote agent asynchronously and get the result
            # run_trading_agent_client now returns a bool indicating whether to buy
            is_indicating = run_async(run_trading_agent_client(clean_stock_code, base_url))

            # Convert result to trade type
            indicating = Trade.indicating if is_indicating else Trade.not_indicating

            # Update trading record
            update_rule_trading(db, rule_id, indicating, stock_code, indicating_date)
            print(f'Result from Remote Agent {rule_id}: {stock_code} is {indicating}!')

            # Update rule's updated_at timestamp
            rule_record.updated_at = datetime.now()
            db.session.commit()

            return {
                'success': True,
                'stock_code': stock_code,
                'indicating': indicating,
                'result': is_indicating
            }

        except Exception as e:
            print(f'Error running remote agent {rule_id} for stock {stock_code}: {e}')
            import traceback
            traceback.print_exc()

            # Mark as not indicating on error
            indicating = Trade.not_indicating
            update_rule_trading(db, rule_id, indicating, stock_code, indicating_date)
            db.session.commit()

            return {
                'success': False,
                'stock_code': stock_code,
                'error': str(e)
            }

    # Handle local agent (original logic)
    # Track child processes created by this invocation
    children_before = set(multiprocessing.active_children())

    try:
        # Get module path from info field
        module_path = rule_record.info
        if not module_path:
            raise ValueError(f"Local agent {rule_id} must have a module path in info field")

        # Dynamically import and execute agent function
        agent_func = get_agent_func(module_path)
        if agent_func is None:
            raise ValueError(f"Failed to import agent from module path: {module_path}")

        # Strip stock exchange suffix (e.g., '600519.SH' -> '600519')
        clean_stock_code = stock_code.split('.')[0] if '.' in stock_code else stock_code
        result = run_async(agent_func(clean_stock_code))

        # Convert result to trade type
        indicating = Trade.indicating if result is True else Trade.not_indicating

        # Update trading record
        update_rule_trading(db, rule_id, indicating, stock_code, indicating_date)
        print(f'Result from Agent {rule_id}: {stock_code} is {indicating}!')

        # Update rule's updated_at timestamp
        rule_record.updated_at = datetime.now()
        db.session.commit()

        return {
            'success': True,
            'stock_code': stock_code,
            'indicating': indicating,
            'result': result
        }

    except Exception as e:
        print(f'Error running agent {rule_id} for stock {stock_code}: {e}')
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'stock_code': stock_code,
            'error': str(e)
        }
    finally:
        # Only clean up child processes created by this invocation
        children_after = set(multiprocessing.active_children())
        new_children = children_after - children_before

        for p in new_children:
            try:
                p.terminate()
                p.join(timeout=5)  # Wait up to 5 seconds for graceful termination
                if p.is_alive():
                    p.kill()  # Force kill if still alive
                    p.join()
            except Exception as e:
                print(f'Error terminating child process: {e}')


def run_agent(db, rule_id):
    """
    Run an agent-type rule for all stocks in its pools.

    Args:
        db: Database session
        rule_id: Agent rule ID
    """
    buying_stocks_list = get_agent_buying_stocks(db, rule_id)
    print(f'Buying stocks for today are: {buying_stocks_list}')

    for stock_code in buying_stocks_list:
        run_agent_for_stock(db, rule_id, stock_code)
