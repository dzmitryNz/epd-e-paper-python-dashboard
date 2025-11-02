#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests
import logging
import os
from typing import Dict, Any, Optional

def get_json_value(data: Dict, path: str) -> Any:
    """Extracts value from JSON by path like 'main.temp' or 'weather[0].description'"""
    keys = path.split('.')
    current = data
    
    for key in keys:
        if '[' in key and ']' in key:
            name, index = key.split('[')
            index = int(index.rstrip(']'))
            if name:
                current = current[name]
            current = current[index]
        else:
            current = current[key]
    
    return current

def format_value(value: Any, value_config: Dict[str, Any]) -> Any:
    """Formats value according to configuration"""
    value_type = value_config.get('type', 'string')
    if value_type == 'int':
        return int(value)
    elif value_type == 'float':
        result = float(value)
        if 'round' in value_config:
            return round(result, value_config['round'])
        return result
    return str(value)

def fetch_weather_data(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetches weather data from API"""
    service_config = config.get('services', {}).get('weather', {})
    url = service_config.get('url', '')
    params = service_config.get('params', {})
    data_config = service_config.get('data', {})
    
    if not url:
        logging.error("Weather URL not set in configuration")
        return None
    
    try:
        processed_params = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith('env.'):
                env_var = value[4:]
                processed_params[key] = os.environ.get(env_var, value)
            elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                processed_params[key] = os.environ.get(env_var, value)
            else:
                processed_params[key] = value
        
        response = requests.get(url, params=processed_params, timeout=10)
        response.raise_for_status()
        weather_raw = response.json()
        
        weather_data = {}
        for key, value_config in data_config.items():
            path = value_config.get('path', key)
            try:
                raw_value = get_json_value(weather_raw, path)
                weather_data[key] = format_value(raw_value, value_config)
            except (KeyError, IndexError, ValueError) as e:
                logging.warning(f"Failed to extract {key} from weather data: {e}")
                weather_data[key] = None
        
        if 'city' in weather_raw:
            weather_data['city'] = weather_raw['name']
        
        logging.info(f"Weather data received: {weather_data}")
        return weather_data
    except requests.RequestException as e:
        logging.error(f"Error fetching weather data: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error processing weather data: {e}")
        return None

