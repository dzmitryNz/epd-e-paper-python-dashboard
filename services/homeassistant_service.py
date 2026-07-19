#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests
import logging
from typing import Dict, Any, Optional

def fetch_homeassistant_data(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetches entity states from the Home Assistant REST API.

    services.homeassistant.entities maps a short dashboard key to a full
    Home Assistant entity_id, e.g. {"gate_door": "binary_sensor.garage_door"}.
    A single entity failing to fetch does not abort the others."""
    service_config = config.get('services', {}).get('homeassistant', {})
    url = service_config.get('url', '')
    token = service_config.get('token', '')
    entities = service_config.get('entities', {})

    if not url or not entities:
        logging.error("Home Assistant URL or entities not set in configuration")
        return None

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    result = {}

    for key, entity_id in entities.items():
        try:
            response = requests.get(f'{url}/api/states/{entity_id}', headers=headers, timeout=10)
            response.raise_for_status()
            result[key] = response.json().get('state')
        except requests.RequestException as e:
            logging.error(f"Error fetching Home Assistant entity {entity_id}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error processing Home Assistant entity {entity_id}: {e}")

    if not result:
        return None

    logging.info(f"Home Assistant data received: {result}")
    return result
