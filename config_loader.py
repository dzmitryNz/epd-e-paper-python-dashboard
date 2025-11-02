#!/usr/bin/python
# -*- coding:utf-8 -*-
import json
import os
import logging
from typing import Dict, Any, Optional

def load_config(config_path: str = 'dashboard.config.json') -> Optional[Dict[str, Any]]:
    """Loads configuration from JSON file"""
    try:
        if not os.path.exists(config_path):
            logging.error(f"Configuration file not found: {config_path}")
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        logging.info(f"Configuration loaded from {config_path}")
        return config
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error in {config_path}: {e}")
        return None
    except IOError as e:
        logging.error(f"File reading error {config_path}: {e}")
        return None

def validate_config(config: Dict[str, Any]) -> bool:
    """Validates configuration structure"""
    required_sections = ['display', 'fonts', 'layout', 'services', 'dashboard']
    
    for section in required_sections:
        if section not in config:
            logging.error(f"Missing required section: {section}")
            return False
    
    if 'display' not in config or 'epdDisplayType' not in config['display']:
        logging.error("Display type missing in configuration")
        return False
    
    if 'services' not in config or not isinstance(config['services'], dict):
        logging.error("Services section must be a dictionary")
        return False
    
    if 'dashboard' not in config or 'lines' not in config['dashboard']:
        logging.error("Missing dashboard.lines section")
        return False
    
    logging.info("Configuration is valid")
    return True

def get_display_colour(config: Dict[str, Any], colour_name: str, default_colour: str = "BLACK") -> str:
    """Gets display color from configuration"""
    display_colours = config.get('display', {})
    colour_key = f"epdColour{colour_name}"
    if colour_key in display_colours:
        return display_colours[colour_key]
    
    return default_colour

