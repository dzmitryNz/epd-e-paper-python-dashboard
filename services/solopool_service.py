#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests
import logging
from typing import Dict, Any, Optional

def fetch_solopool_data(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetches mining pool stats from solopool API"""
    service_config = config.get('services', {}).get('solopool', {})
    url = service_config.get('url', '')

    if not url:
        logging.error("Solopool URL not set in configuration")
        return None

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        solopool_raw = response.json()
        stats = solopool_raw.get('stats', {})

        solopool_data = {
            'hashrate': solopool_raw.get('hashrate', 0),
            'luck': solopool_raw.get('luck', 0),
            'blocks': stats.get('blocksFound', 0),
        }

        logging.info(f"Solopool data received: {solopool_data}")
        return solopool_data
    except requests.RequestException as e:
        logging.error(f"Error fetching solopool data: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error processing solopool data: {e}")
        return None
