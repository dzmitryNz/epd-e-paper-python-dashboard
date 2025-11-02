#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import logging

from config_loader import load_config, validate_config
from data_loader import load_all_data
from data_storage import save_data
from display_renderer import DisplayRenderer

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    try:
        config_path = 'dashboard.config.json'
        
        logging.info("Loading configuration...")
        config = load_config(config_path)
        if not config:
            logging.error("Failed to load configuration")
            return
        
        if not validate_config(config):
            logging.error("Configuration is invalid")
            return
        
        logging.info("Loading data from all sources...")
        all_data, data_ages = load_all_data(config, use_cache=True)
        
        save_data(all_data)
        
        logging.info("Initializing display renderer...")
        renderer = DisplayRenderer(config)
        renderer.init_display()
        
        logging.info("Rendering data on display...")
        image = renderer.render(all_data, data_ages)
        
        needs_full_refresh = any(
            any(ages.values()) if isinstance(ages, dict) and ages else False 
            for ages in data_ages.values()
        )
        renderer.display_image(image, full_refresh=needs_full_refresh)
        renderer.sleep()
        
        logging.info("Completed successfully")
        
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        try:
            from waveshare_epd import epd2in15g
            epd2in15g.epdconfig.module_exit(cleanup=True)
        except:
            pass
        sys.exit(0)
    except Exception as e:
        logging.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()

