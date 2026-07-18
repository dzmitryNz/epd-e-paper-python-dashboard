#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import time
import locale
import logging

os.chdir(os.path.dirname(os.path.realpath(__file__)))

from config_loader import load_env_file, load_config, validate_config
from data_loader import load_all_data
from data_storage import save_data
from display_renderer import DisplayRenderer
from verbs import (load_verbs, load_verbs_state, save_verbs_state,
                   advance_verbs_page)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SAVED_IMAGE_PATH = 'saved_display_image.png'
VERBS_UPDATE_INTERVAL = 300  # seconds between verbs page flips


def main():
    dry_run = '--dry-run' in sys.argv

    try:
        locale.setlocale(locale.LC_TIME, 'be_BY.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, '')

    load_env_file()
    config = load_config()
    if config is None or not validate_config(config):
        logging.error("Invalid configuration, exiting")
        sys.exit(1)

    verbs_list = load_verbs()
    verbs_state = load_verbs_state()
    current_page = verbs_state.get('current_page', 0)
    last_verbs_update = verbs_state.get('last_update_time', 0)
    now = time.time()

    all_data, data_ages = load_all_data(config)
    save_data(all_data)

    renderer = DisplayRenderer(config)
    if not dry_run:
        renderer.init_display()

    image = renderer.render(all_data, data_ages, verbs=verbs_list, verbs_page=current_page)
    renderer.display_image(image)
    image.save(SAVED_IMAGE_PATH)
    logging.info(f"Saved display image to {SAVED_IMAGE_PATH}")

    if now - last_verbs_update >= VERBS_UPDATE_INTERVAL:
        verbs_per_page = renderer.verbs_per_page()
        if verbs_list and verbs_per_page > 0:
            current_page = advance_verbs_page(current_page, len(verbs_list), verbs_per_page)
            logging.info(f"Switching verbs page to {current_page + 1}")

            image = renderer.refresh_verbs_area(image, verbs_list, current_page)
            renderer.display_image(image)
            image.save(SAVED_IMAGE_PATH)

            verbs_state['current_page'] = current_page
            verbs_state['last_update_time'] = now
            save_verbs_state(verbs_state)

    renderer.sleep()


if __name__ == '__main__':
    try:
        main()
    except IOError as e:
        logging.error(e)
    except KeyboardInterrupt:
        logging.info("Interrupted")
        sys.exit(0)
