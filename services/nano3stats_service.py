#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests
import logging
import json
import re
from typing import Dict, Any, Optional

def parse_jsonp(text: str, callback: str = 'dashboardCallback') -> Optional[Dict[str, Any]]:
    """Extracts JSON payload from a JSONP response like 'dashboardCallback({...});'.
    Tolerates trailing commas in objects and arrays."""
    start_marker = callback + '('
    start_idx = text.find(start_marker)
    if start_idx == -1:
        return None

    end_idx = text.rfind(');')
    if end_idx == -1:
        return None

    json_str = text[start_idx + len(start_marker):end_idx].strip()
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSONP payload: {e}")
        return None

def fetch_nano3stats_data(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetches miner dashboard stats from nano3 JSONP endpoint"""
    service_config = config.get('services', {}).get('nano3stats', {})
    url = service_config.get('url', '')
    auth_cookie = service_config.get('authCookie', '')

    if not url:
        logging.error("Nano3stats URL not set in configuration")
        return None

    try:
        cookies = {'auth': auth_cookie} if auth_cookie else None
        response = requests.get(url, cookies=cookies, timeout=10)
        response.raise_for_status()

        parsed = parse_jsonp(response.text.strip())
        if parsed is None:
            logging.error(f"Unexpected response format from nano3stats: {response.text[:100]}")
            return None

        nano3stats_data = {
            'workingmode': parsed.get('workingmode', '0'),
            'workingstatus': parsed.get('workingstatus', '0'),
            'power': parsed.get('power', '0'),
        }

        logging.info(f"Nano3stats data received: {nano3stats_data}")
        return nano3stats_data
    except requests.RequestException as e:
        logging.error(f"Error fetching nano3stats data: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error processing nano3stats data: {e}")
        return None
