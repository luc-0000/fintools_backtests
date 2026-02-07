#!/usr/bin/env python
# encoding=utf8

"""
Pure SQLAlchemy Database Initialization for FastAPI
This module provides database initialization without Flask dependencies
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from end_points.common.const.consts import DataBase
from end_points.config.global_var import global_var


class DatabaseWrapper:
    """
    Database wrapper that mimics Flask-SQLAlchemy interface
    to maintain compatibility with existing code
    """
    def __init__(self, session, engine=None, engines=None):
        self.session = session
        self.engine = engine
        self.engines = engines or {}

    def get_engine(self, bind_key=None):
        """Get engine for specific bind_key"""
        if bind_key is None:
            return self.engine
        return self.engines.get(bind_key, self.engine)


def init_db_for_fastapi(config, global_var):
    """
    Initialize database using pure SQLAlchemy

    Args:
        config: Configuration dictionary
        global_var: Global variables dictionary

    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        db_user = config.get('DB_USER')
        db_password = config.get('DB_PASSWORD')
        db_host = config.get('DB_HOST')
        db_port = config.get('DB_PORT')
        db_name = config.get('DB_NAME', 'cn_stocks_in_pool')

        # Create database URI
        db_base_uri = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/'

        # Create main engine with optimized pool settings
        main_db_uri = db_base_uri + db_name
        engine = create_engine(
            main_db_uri,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=5,  # Reduced from 10 - will grow as needed
            max_overflow=15,  # Reduced from 20
            echo=False
        )

        # Create engines for all bind keys (multiple databases)
        bind_engines = {}
        bind_uris = {
            DataBase.stocks: db_base_uri + DataBase.stocks,
            DataBase.stocks_m: db_base_uri + DataBase.stocks_m,
            DataBase.stocks_in_pool: db_base_uri + DataBase.stocks_in_pool,
            # DH/DQ databases removed - all use the same stocks database
        }

        for bind_key, bind_uri in bind_uris.items():
            bind_engines[bind_key] = create_engine(
                bind_uri,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=3,
                max_overflow=10,
                echo=False
            )

        # Create scoped session
        session_factory = sessionmaker(bind=engine)
        Session = scoped_session(session_factory)

        # Create database wrapper with multiple engines
        db_wrapper = DatabaseWrapper(Session, engine=engine, engines=bind_engines)

        # Store in global_var
        global_var['db'] = db_wrapper
        global_var['db_engine'] = engine
        global_var['db_session'] = Session
        global_var['db_engines'] = bind_engines

        # Store bind information for multiple databases
        global_var['db_binds'] = bind_uris

        print(f"Database initialized successfully: {main_db_uri}")
        return True, ''

    except Exception as e:
        print(f"Failed to initialize database: {e}")
        return False, str(e)


def get_db_session():
    """
    Get database session for dependency injection

    Returns:
        SQLAlchemy session
    """
    # from end_points.config.global_var import global_var
    return global_var.get('db')
