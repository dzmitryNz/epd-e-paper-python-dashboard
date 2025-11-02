#!/usr/bin/python
# -*- coding:utf-8 -*-
import json
import os
import logging
from typing import Dict, Any, Optional

DEFAULT_DATA_FILE = 'dashboard_data.json'

def load_data(data_file: str = DEFAULT_DATA_FILE) -> Dict[str, Any]:
    """Loads saved data from file"""
    if not os.path.exists(data_file):
        logging.debug(f"Data file not found: {data_file}")
        return {}
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logging.debug(f"Data loaded from {data_file}")
        return data
    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Failed to load data from {data_file}: {e}")
        return {}

def save_data(data: Dict[str, Any], data_file: str = DEFAULT_DATA_FILE) -> bool:
    """Saves data to file"""
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.debug(f"Data saved to {data_file}")
        return True
    except IOError as e:
        logging.error(f"Failed to save data to {data_file}: {e}")
        return False

def get_cached_value(data: Dict[str, Any], key: str, sub_key: Optional[str] = None) -> Optional[Any]:
    """Gets cached value by key"""
    if sub_key:
        if key in data and sub_key in data[key]:
            return data[key][sub_key]
    else:
        if key in data:
            return data[key]
    return None

def is_valid_value(value: Any) -> bool:
    """Checks if value is valid (not empty, not ERR)"""
    if value is None:
        return False
    value_str = str(value).strip()
    return value_str and value_str != 'ERR' and value_str != 'N/A'

