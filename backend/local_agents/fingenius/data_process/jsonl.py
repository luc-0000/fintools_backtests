import json
import os
import sys
import uuid
from datetime import datetime, time
from pathlib import Path

from flask import Flask

from end_points.app.init_global import init_global, global_var
from end_points.common.const.consts import Trade
from db_models.db_models import SimTrading, Simulator


def to_jsonl(db):
    rule_id = 3000
    input_dict = "/Users/lu/development/ai/ai_money/am_backend/agent_rules/fingenius/reports"  # 存放JSON文件的文件夹
    output_jsonl_file = "/Users/lu/development/ai/ai_money/am_backend/agent_rules/fingenius/data_process/data/output.jsonl"  # 输出的JSONL文件
    all_dates = get_subdir(input_dict)
    all_dates.sort()
    for each_date in all_dates:
        input_files = input_dict + '/' + each_date
        # output_jsonl_file = output_jsonl_dir + 'fg_' + each_date + '.jsonl'
        json_files_to_jsonl(db, rule_id, each_date, input_files, output_jsonl_file)
    return

def json_files_to_jsonl(db, rule_id, trading_date, input_dir, output_file):
    """
    将指定目录下的所有JSON文件内容转换为JSONL格式，每个文件内容占一行。

    Args:
        input_dir (str): 包含JSON文件的输入目录路径
        output_file (str): 输出的JSONL文件路径
    """
    input_path = Path(input_dir)

    # 查找目录下所有的.json文件
    json_files = list(input_path.glob("*.json"))

    if not json_files:
        print(f"在目录 {input_dir} 中未找到JSON文件。")
        return

    print(f"找到 {len(json_files)} 个JSON文件，开始转换...")
    success_count = 0

    with open(output_file, 'a', encoding='utf-8') as outfile:
        for json_file in json_files:
            try:
                # 读取JSON文件内容
                with open(json_file, 'r', encoding='utf-8') as infile:
                    # 加载JSON数据，此处会验证JSON格式是否有效
                    file_content = json.load(infile)
                stock_code = file_content.get('stock_code')
                earning = get_earning(db, rule_id, stock_code, trading_date)
                if earning is not None:
                    # file_content.update({'return': str(earning) + '%'})
                    task_dict = {
                        'id': str(uuid.uuid4()),
                        'task_input': file_content,
                        'trading_return': earning
                    }

                    # 将整个文件内容作为一个对象写入JSONL，并添加换行符
                    json_line = json.dumps(task_dict, ensure_ascii=False)
                    outfile.write(json_line + '\n')

                    success_count += 1
                    print(f"✓ 已处理: {json_file.name}")

            # except json.JSONDecodeError as e:
            #     print(f"✗ 错误：文件 {json_file.name} 包含无效的JSON格式 - {e}")
            except Exception as e:
                print(f"✗ 处理文件 {json_file.name} 时发生错误 - {e}")
                raise

    print(f"转换完成！成功处理 {success_count}/{len(json_files)} 个文件。结果保存在 {output_file}")


def get_earning(db, rule_id, stock_code, trading_date):
    earning = None
    sim_id = db.session.query(Simulator.id).filter(Simulator.rule_id == rule_id).scalar()
    start_date = datetime.strptime(trading_date, "%Y-%m-%d")

    query = (db.session.query(SimTrading)
             .filter(SimTrading.sim_id == sim_id)
             .filter(SimTrading.trading_date >= start_date)
             .filter(SimTrading.stock == stock_code))
    buy_query = query.filter(SimTrading.trading_type == Trade.buy).filter(SimTrading.trading_date == trading_date).first()
    sell_query = query.filter(SimTrading.trading_type == Trade.sell).first()
    if buy_query is not None and sell_query is not None:
        buy_amount = buy_query.trading_amount
        sell_amount = sell_query.trading_amount
        earning = round((sell_amount - buy_amount)*100/buy_amount, 2)
    return earning


def get_subdir(path):
    """获取指定路径下的直接子目录名称列表"""
    try:
        entries = os.listdir(path)
        subdirs = [entry for entry in entries if os.path.isdir(os.path.join(path, entry))]
        return subdirs
    except Exception as e:
        print(e)
        return []


if __name__ == '__main__':
    env = 'local'
    # env = 'morning'
    all_args = sys.argv[1:]
    if len(all_args) > 0:
        env = all_args[0]
    app = Flask(__name__)
    env_dist = os.environ
    if env == 'yunxiao':
        config_file = env_dist.get('CFG_PATH', '../../../service_dlc.conf')
    else:
        config_file = env_dist.get('CFG_PATH', '../../../service.conf')
    app.config.from_pyfile(config_file, silent=True)
    init_global(app)
    db = global_var["db"]
    with app.app_context():
        to_jsonl(db)