#!/usr/bin/python
# -*- coding:utf-8 -*-
import json
import os
import logging
from typing import Dict, Any, List

DEFAULT_VERBS_FILE = 'verbs.json'
DEFAULT_STATE_FILE = 'verbs_state.json'

DEFAULT_VERBS = [
    {"infinitive": "go", "past": "went", "past_participle": "gone", "translation": "ісці"},
    {"infinitive": "see", "past": "saw", "past_participle": "seen", "translation": "бачыць"},
    {"infinitive": "come", "past": "came", "past_participle": "come", "translation": "прыходзіць"},
    {"infinitive": "know", "past": "knew", "past_participle": "known", "translation": "ведаць"},
    {"infinitive": "get", "past": "got", "past_participle": "got", "translation": "атрымліваць"},
]

def load_verbs(verbs_file: str = DEFAULT_VERBS_FILE) -> List[Dict[str, Any]]:
    """Loads verbs list from JSON file, creating it with defaults when missing"""
    if os.path.exists(verbs_file):
        try:
            with open(verbs_file, 'r', encoding='utf-8') as f:
                verbs = json.load(f)
            logging.info(f"Loaded {len(verbs)} verbs from {verbs_file}")
            return verbs
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Failed to load verbs from {verbs_file}: {e}")

    try:
        with open(verbs_file, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_VERBS, f, indent=2, ensure_ascii=False)
        logging.info(f"Created default verbs file {verbs_file}")
    except IOError as e:
        logging.error(f"Failed to create verbs file: {e}")

    return list(DEFAULT_VERBS)

def load_verbs_state(state_file: str = DEFAULT_STATE_FILE) -> Dict[str, Any]:
    """Loads verbs pagination state from file"""
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Failed to load verbs state from {state_file}: {e}")

    return {'current_page': 0, 'last_update_time': 0}

def save_verbs_state(state: Dict[str, Any], state_file: str = DEFAULT_STATE_FILE) -> bool:
    """Saves verbs pagination state to file"""
    try:
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except IOError as e:
        logging.error(f"Failed to save verbs state to {state_file}: {e}")
        return False

def calculate_verbs_per_page(line_height: int, max_height: int) -> int:
    """Calculates how many verbs fit into the given area height"""
    if max_height <= 0:
        return 0
    return max(1, max_height // line_height)

def advance_verbs_page(current_page: int, total_verbs: int, verbs_per_page: int) -> int:
    """Returns the next page index, wrapping around at the end"""
    if total_verbs <= 0 or verbs_per_page <= 0:
        return 0
    total_pages = (total_verbs + verbs_per_page - 1) // verbs_per_page
    return (current_page + 1) % total_pages
