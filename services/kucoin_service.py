#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests
import logging
from typing import Dict, Any, Optional

def format_value(value: Any, value_config: Dict[str, Any]) -> Any:
    """Formats value according to configuration"""
    value_type = value_config.get('type', 'string')
    if value_type == 'int':
        return int(float(value))
    elif value_type == 'float':
        result = float(value)
        if 'round' in value_config:
            return round(result, value_config['round'])
        return result
    return str(value)

def fetch_kucoin_data(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetches cryptocurrency data from KuCoin API"""
    service_config = config.get('services', {}).get('kucoin', {})
    url = service_config.get('url', '')
    pairs = service_config.get('pairs', [])
    data_config = service_config.get('data', {})
    
    if not url:
        logging.error("KuCoin URL not set in configuration")
        return None
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        kucoin_raw = response.json()
        
        if kucoin_raw.get('code') != '200000':
            logging.error(f"KuCoin API error: {kucoin_raw.get('msg', 'Unknown error')}")
            return None
        
        ticker_data = kucoin_raw.get('data', {}).get('ticker', [])
        ticker_dict = {ticker.get('symbol'): ticker for ticker in ticker_data}
        
        kucoin_data = {}
        for pair in pairs:
            if pair in ticker_dict:
                ticker = ticker_dict[pair]
                pair_config = data_config.get(pair, {})
                
                price_key = pair_config.get('path', 'last')
                if price_key in ticker:
                    price_value = ticker[price_key]
                    formatted_price = format_value(price_value, pair_config)
                    
                    kucoin_data[pair] = {
                        'last': formatted_price,
                        'change_rate': float(ticker.get('changeRate', 0)),
                        'change_price': float(ticker.get('changePrice', 0))
                    }
        
        logging.info(f"KuCoin data received: {list(kucoin_data.keys())}")
        return kucoin_data
    except requests.RequestException as e:
        logging.error(f"Error fetching KuCoin data: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error processing KuCoin data: {e}")
        return None

