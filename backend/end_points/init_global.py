#!/usr/bin/env python
# encoding=utf8

"""
FastAPI Global Initialization Module

This module provides initialization functions for FastAPI that are compatible
with the existing init_global system used in Flask.
"""

import os
import pymysql

from end_points.config.db_init import init_db_for_fastapi
from end_points.config.global_var import global_var

pymysql.install_as_MySQLdb()


def load_config_file(config_path: str) -> dict:
    """
    Load configuration from a file (Flask-style .conf file)

    Args:
        config_path: Path to the configuration file

    Returns:
        Dictionary with configuration values
    """
    config = {}

    if not os.path.exists(config_path):
        print(f"Warning: Config file not found at {config_path}")
        return config

    try:
        # Try to read as Python file (Flask style)
        with open(config_path, 'r', encoding='utf-8') as f:
            exec(f.read(), config)

        # Remove built-in variables
        config = {k: v for k, v in config.items()
                  if not k.startswith('__')}

    except Exception as e:
        print(f"Error loading config file: {e}")

    return config


def init_global(config_path: str = None):
    """
    Initialize global variables for FastAPI application

    Args:
        config_path: Path to the configuration file

    Returns:
        bool: True if initialization successful, False otherwise
    """
    if config_path is None:
        # Use service.conf in project root (one level up from end_points/)
        config_path = os.environ.get('CFG_PATH', os.path.join(os.path.dirname(__file__), '..', 'service.conf'))

    # Make path absolute
    if not os.path.isabs(config_path):
        config_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), config_path
        ))

    # Load configuration
    config = load_config_file(config_path)

    if not config:
        print("Warning: Using default configuration")
        # Set default values
        config = {
            'VERSION_FILE': './version.txt',
            'DB_USER': os.environ.get('DB_USER', 'root'),
            'DB_PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'DB_HOST': os.environ.get('DB_HOST', 'localhost'),
            'DB_PORT': os.environ.get('DB_PORT', '3306'),
            'DB_NAME': os.environ.get('DB_NAME', 'fintools_backtest'),
        }

    # Read version
    try:
        version_file = config.get('VERSION_FILE', './version.txt')
        if os.path.exists(version_file):
            with open(version_file, 'r', encoding='utf-8') as f:
                version = f.read().strip()
        else:
            version = 'unknown'
    except Exception as e:
        print(f"Warning: Could not read version file: {e}")
        version = 'unknown'

    global_var['version'] = version

    # Initialize database
    ok, err_msg = init_db_for_fastapi(config, global_var)
    if not ok:
        print(f'Failed to init database: {err_msg}')
        return False

    # # Initialize data tool
    # ok, err_msg = init_data_tool_for_fastapi(config, global_var)
    # if not ok:
    #     print(f'Failed to init data tool: {err_msg}')
    #     return False

    print("FastAPI global initialization completed successfully")
    return True