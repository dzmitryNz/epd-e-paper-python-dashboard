#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests
import logging
from typing import Dict, Any, Optional, List

def parse_sensor_text(text: str) -> Dict[str, str]:
    """Parses sensor text data in format 'key1:value1;key2:value2'"""
    sensor_dict = {}
    if not text:
        return sensor_dict
    
    pairs = text.strip().split(';')
    for pair in pairs:
        if ':' in pair:
            key, value = pair.split(':', 1)
            sensor_dict[key.strip()] = value.strip()
    
    return sensor_dict

def format_value(value: str, value_config: Dict[str, Any]) -> Any:
    """Formats value according to configuration"""
    if not value:
        return None
    
    value_type = value_config.get('type', 'string')
    try:
        if value_type == 'int':
            return int(float(value))
        elif value_type == 'float':
            result = float(value)
            if 'round' in value_config:
                return round(result, value_config['round'])
            return result
    except (ValueError, TypeError):
        pass
    
    return str(value)

def fetch_sensor_data(config: Dict[str, Any], service_key: str) -> Optional[Dict[str, str]]:
    """Fetches sensor data from specified service"""
    service_config = config.get('services', {}).get(service_key, {})
    url = service_config.get('url', '')
    data_config = service_config.get('data', {})
    response_type = service_config.get('responseType', 'text')
    
    if not url:
        logging.error(f"URL for {service_key} not set in configuration")
        return None
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        sensor_data = {}
        if response_type == 'text':
            raw_text = response.text.strip()
            parsed = parse_sensor_text(raw_text)
            
            for key, value_config in data_config.items():
                path = value_config.get('path', key)
                if path in parsed:
                    raw_value = parsed[path]
                    sensor_data[key] = format_value(raw_value, value_config)
        elif response_type == 'json':
            raw_json = response.json()
            for key, value_config in data_config.items():
                path = value_config.get('path', key)
                try:
                    if '.' in path:
                        parts = path.split('.')
                        current = raw_json
                        for part in parts:
                            current = current[part]
                        raw_value = current
                    else:
                        raw_value = raw_json[path]
                    sensor_data[key] = format_value(str(raw_value), value_config)
                except (KeyError, TypeError):
                    logging.warning(f"Failed to extract {key} from sensor data")
        sensor_data[key] = None
        
        logging.info(f"Sensor data {service_key} received: {list(sensor_data.keys())}")
        return sensor_data
    except requests.RequestException as e:
        logging.error(f"Error fetching sensor data {service_key}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error processing sensor data {service_key}: {e}")
        return None

def fetch_all_sensor_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """Fetches data from all sensor sources"""
    all_sensor_data = {}
    
    service_keys = [key for key in config.get('services', {}).keys() if key.startswith('sensors')]
    
    for service_key in service_keys:
        sensor_data = fetch_sensor_data(config, service_key)
        if sensor_data:
            all_sensor_data.update(sensor_data)
    
    return all_sensor_data
