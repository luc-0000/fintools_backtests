import configparser
import json
import os
import sys
from sqlalchemy import func

# Add project root to Python path so we can import app, common, etc.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from mcp_servers.utils import get_mcp_studio_tools_async
from mcp_servers.database_mcp_servers.get_database_mcp_utils import get_sims_for_type, get_sim_result
from end_points.get_earn.earn_schema import StockRuleEarnSchema
from db.mysql.db_schemas import Simulator, Rule, StockRuleEarn, Stock
from micro_models.dl_models.training.LSTM.train.train_utils import transform_config, init_session
from mcp.server.fastmcp import FastMCP
from end_points.common.const.consts import RuleType, Status

tool_kit_name = "DatabaseTool"
get_database_mcp = FastMCP(tool_kit_name)
global_session = None

@get_database_mcp.tool()
def get_sim_results_for_type(rule_type = RuleType.model_close):
    """Get All Simlator Results for Sepecific Rule Type"""
    try:
        sims = get_sims_for_type(global_session, rule_type)
        sim_results = []
        for sim_id in sims:
            each_sim_result = get_sim_result(global_session, sim_id)
            sim_results.append(each_sim_result)
        pretty_result = json.dumps(sim_results, indent=4, sort_keys=True)
        return pretty_result
    except Exception as e:
        print(e)
    finally:
        global_session.close()

@get_database_mcp.tool()
def get_indicating_stocks():
    """Get All indicating stocks"""
    try:
        rows = (global_session.query(StockRuleEarn, Rule.type.label('rule_type'), Rule.name.label("rule_name"), Stock.name.label("stock_name"), Rule.created_at)
                .join(Rule, Rule.id == StockRuleEarn.rule_id)
                .join(Stock, Stock.code == StockRuleEarn.stock_code)
                .filter(StockRuleEarn.status == Status.indicating)
                .filter(Rule.type == RuleType.model_close).all())
        data = []
        for stock_earn, rule_type, rule_name, stock_name, created_at in rows:
            # Convert SQLAlchemy model to dict and add joined fields
            earn_dict = StockRuleEarnSchema.model_validate(stock_earn).model_dump(mode='json')
            earn_dict['rule_type'] = rule_type
            earn_dict['rule_name'] = rule_name
            earn_dict['stock_name'] = stock_name
            earn_dict['created_at'] = created_at.strftime("%Y-%m-%d %H:%M:%S")
            data.append(earn_dict)

        # Add metadata to help LLM understand the data
        result = {
            "description": "List of stocks with indicating status (buy signals) from machine learning trading models",
            "field_descriptions": {
                "stock_code": "Stock ticker symbol",
                "stock_name": "Name of the stock company",
                "rule_id": "ID of the trading rule/model that generated this signal",
                "rule_name": "Name of the trading rule/model",
                "rule_type": "Type of trading rule (mclose = model close price prediction)",
                "earn": "Total profit/loss in percentage from all trades",
                "avg_earn": "Average profit/loss per trade in percentage",
                "earning_rate": "Win rate - percentage of profitable trades",
                "trading_times": "Total number of trades executed",
                "status": "Current signal status (indicating = buy signal active)",
                "indicating_date": "Date when the buy signal was generated (ISO format)",
                "updated_at": "Last update timestamp (ISO format)",
                "created_at": "Since this rule created, also indicating trading start time for this rule"
            },
            "total_count": len(data),
            "data": data
        }
        pretty_result = json.dumps(result, indent=4, sort_keys=True)
        return pretty_result
    except Exception as e:
        print(e)
    finally:
        global_session.close()


@get_database_mcp.tool()
def get_agent_buying_stocks(sims):
    try:
        # sims = get_agent_sims(db, agent_id)
        sim_stock_set = (global_session.query(func.group_concat(Simulator.id).label('sims'), StockRuleEarn.stock_code, StockRuleEarn.indicating_date)
            .join(Simulator, Simulator.rule_id == StockRuleEarn.rule_id)
            .filter(Simulator.id.in_(sims))
            .filter(StockRuleEarn.status == Status.indicating)
            .group_by(StockRuleEarn.stock_code, StockRuleEarn.indicating_date).all())
        buying_stocks_list = [dict(row._mapping) for row in sim_stock_set]
        return buying_stocks_list
    except Exception as e:
        print(e)
    finally:
        global_session.close()


async def get_database_tools_async():
    current_file_path = os.path.abspath(__file__)
    client, all_tools = await get_mcp_studio_tools_async(current_file_path, tool_kit_name)
    return client, all_tools


if __name__ == '__main__':
    default_config_path = os.path.join(project_root, 'service.conf')
    config_file = os.environ.get('CFG_PATH', default_config_path)
    config = configparser.ConfigParser(converters={'string': (lambda s: s.strip("'"))})
    with open(config_file) as stream:
        config.read_string("[s]\n" + stream.read())
    config = transform_config(config)
    global_session = init_session(config)
    get_database_mcp.run(transport="stdio")