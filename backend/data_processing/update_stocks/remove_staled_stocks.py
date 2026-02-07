import configparser
import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from db.mysql.db_schemas_dynamic import get_stock_model
from end_points.common.const.consts import DataBase
from end_points.common.utils.format import byte_ary_to_str
from end_points.get_stock.operations.get_stock_utils import get_all_stocks

def transform_config(config):
    result = {s: dict(config.items(s)) for s in config.sections()}
    result = result.get('s')
    for each_key in result:
        result[each_key] = result.get(each_key).strip("'")
    db_user = result.get('db_user')
    db_pw = result.get('db_password')
    db_host = result.get('db_host')
    db_port = result.get('db_port')
    result = [db_user, db_pw, db_host, db_port]
    return result

def init_session(config, bind_key=DataBase.ai_stock):
    config = byte_ary_to_str(config)
    db_base_uri = 'mysql+pymysql://%s:%s@%s:%s/' % (config[0], config[1], config[2], config[3])
    database_uri = db_base_uri + ('%s' % (bind_key))
    try:
        engine = create_engine(database_uri)
        # db = engine.connect()
        Session = sessionmaker(bind=engine)
        session = Session()
        print("init database session")
    except Exception as e:
        print(e)
    return session


def remove_stale_stocks(config):
    try:
        engine = init_engine(config)
        inspection = inspect(engine)
        all_tables = inspection.get_table_names()
        ai_stock_session = init_session(config, DataBase.ai_stock)
        all_stocks = get_all_stocks(ai_stock_session)

        with engine.connect() as connection:
            trans = connection.begin()
            try:
                for stock_code in all_tables:
                    if stock_code not in all_stocks:
                        stock_class = get_stock_model(stock_code)
                        stock_class.__table__.drop(engine, checkfirst=True)
                        print("deleted table for stock: {}".format(stock_code))
                trans.commit()
            except Exception as e:
                trans.rollback()
                raise e
    except Exception as e:
        print(e)
    finally:
        print("closing database")
        engine.dispose()
        ai_stock_session.close()
    return

def init_engine(config, bind_key=DataBase.stocks):
    # config = byte_ary_to_str(config)
    db_base_uri = 'mysql+pymysql://%s:%s@%s:%s/' % (config[0], config[1], config[2], config[3])
    database_uri = db_base_uri + ('%s' % (bind_key))
    try:
        engine = create_engine(database_uri)
        # db = engine.connect()
        # Session = sessionmaker(bind=engine)
        # session = Session()
        print("init database")
    except Exception as e:
        print(e)
    return engine

if __name__ == '__main__':
    env_dist = os.environ
    config_file = env_dist.get('CFG_PATH', '../../service.conf')
    config = configparser.ConfigParser(
        converters={'string': (lambda s: s.strip("'"))})
    with open(config_file) as stream:
        config.read_string("[s]\n" + stream.read())
    config = transform_config(config)
    remove_stale_stocks(config)
