#!/usr/bin/python
# -*- coding:utf-8 -*-
import logging
from typing import Dict, Any, Optional
from services.weather_service import fetch_weather_data
from services.kucoin_service import fetch_kucoin_data
from services.sensor_service import fetch_all_sensor_data
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

def load_all_data(config: Dict[str, Any], use_cache: bool = True):
    """Loads data from all sources, using cache when needed.
    Returns data and dictionary of data age flags."""
    cached_data = load_data() if use_cache else {}
    
    all_data = {
        'weather': {},
        'kucoin': {},
        'sensors': {}
    }
    data_ages = {
        'weather': {},
        'kucoin': {},
        'sensors': {}
    }
    
    logging.info("Loading data from all sources...")
    
    weather_data = fetch_weather_data(config)
    if weather_data:
        all_data['weather'], data_ages['weather'] = merge_data_with_cache(weather_data, cached_data, 'weather')
    elif use_cache:
        cached_weather = cached_data.get('weather', {})
        if cached_weather:
            all_data['weather'] = cached_weather.copy()
            for key in cached_weather.keys():
                data_ages['weather'][key] = True
    
    kucoin_data = fetch_kucoin_data(config)
    if kucoin_data:
        all_data['kucoin'], data_ages['kucoin'] = merge_data_with_cache(kucoin_data, cached_data, 'kucoin')
    elif use_cache:
        cached_kucoin = cached_data.get('kucoin', {})
        if cached_kucoin:
            all_data['kucoin'] = cached_kucoin.copy()
            for key in cached_kucoin.keys():
                data_ages['kucoin'][key] = True
    
    sensor_data = fetch_all_sensor_data(config)
    if sensor_data:
        all_data['sensors'], data_ages['sensors'] = merge_data_with_cache(sensor_data, cached_data, 'sensors')
    elif use_cache:
        cached_sensors = cached_data.get('sensors', {})
        if cached_sensors:
            all_data['sensors'] = cached_sensors.copy()
            for key in cached_sensors.keys():
                data_ages['sensors'][key] = True
    
    return all_data, data_ages

