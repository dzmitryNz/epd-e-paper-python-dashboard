#!/usr/bin/python
# -*- coding:utf-8 -*-
import logging
from typing import Dict, Any, Optional
from services.weather_service import fetch_weather_data
from services.kucoin_service import fetch_kucoin_data
from services.sensor_service import fetch_all_sensor_data
from services.solopool_service import fetch_solopool_data
from services.nano3stats_service import fetch_nano3stats_data
from data_storage import load_data, is_valid_value, get_cached_value

def merge_data_with_cache(current_data: Optional[Dict[str, Any]], 
                         cached_data: Dict[str, Any], 
                         data_key: str):
    """Merges current data with cached data, using cache if current is invalid.
    Returns data and dictionary of flags indicating which values are old."""
    result = {}
    age_flags = {}
    
    if current_data:
        for key, value in current_data.items():
            if is_valid_value(value):
                result[key] = value
                age_flags[key] = False
            else:
                cached_value = get_cached_value(cached_data, data_key, key)
                if cached_value is not None:
                    result[key] = cached_value
                    age_flags[key] = True
                else:
                    result[key] = value
                    age_flags[key] = False
    else:
        cached_item = cached_data.get(data_key, {})
        if cached_item:
            result = cached_item.copy()
            for key in result.keys():
                age_flags[key] = True
    
    return result, age_flags

DATA_SOURCES = {
    'weather': 'fetch_weather_data',
    'kucoin': 'fetch_kucoin_data',
    'sensors': 'fetch_all_sensor_data',
    'solopool': 'fetch_solopool_data',
    'nano3stats': 'fetch_nano3stats_data',
}

def load_all_data(config: Dict[str, Any], use_cache: bool = True):
    """Loads data from all sources, using cache when needed.
    Returns data and dictionary of data age flags."""
    cached_data = load_data() if use_cache else {}

    all_data = {category: {} for category in DATA_SOURCES}
    data_ages = {category: {} for category in DATA_SOURCES}

    logging.info("Loading data from all sources...")

    for category, fetch_name in DATA_SOURCES.items():
        current = globals()[fetch_name](config)
        if current:
            all_data[category], data_ages[category] = merge_data_with_cache(current, cached_data, category)
        elif use_cache:
            cached_category = cached_data.get(category, {})
            if cached_category:
                all_data[category] = cached_category.copy()
                for key in cached_category.keys():
                    data_ages[category][key] = True

    return all_data, data_ages

