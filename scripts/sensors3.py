#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd2in15g
import time
from PIL import Image,ImageDraw,ImageFont
import traceback
import requests
import json
import os

# Parse command line arguments
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Sensor data file
SENSOR_DATA_FILE = 'sensor_data.json'

def load_sensor_data():
    """Load cached sensor data from file"""
    if os.path.exists(SENSOR_DATA_FILE):
        try:
            with open(SENSOR_DATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Failed to load sensor data from file: {e}")
    return {}

def save_sensor_data(sensor_data):
    """Save sensor data to file"""
    try:
        with open(SENSOR_DATA_FILE, 'w') as f:
            json.dump(sensor_data, f, indent=2)
        logging.debug(f"Saved sensor data to {SENSOR_DATA_FILE}")
    except IOError as e:
        logging.error(f"Failed to save sensor data to file: {e}")

def is_valid_value(value):
    """Check if sensor value is valid (not empty, not ERR)"""
    return value and value.strip() and value.strip() != 'ERR'

url = 'http://192.168.0.106/sensors'  # default URL
url2 = 'http://192.168.0.100/sensors'  # default URL
show_sensor_names = ['dsw1', 'dsw2', 'bpmt', 'bmpp']
sensor_names = { 'dsw1': 'Outside', 'dsw2': 'Balcony', 'bpmt': 'BK', 'bmpp': 'Press' }
sensor_units = { 'dsw1': '°C', 'dsw2': '°C', 'bpmt': '°C', 'bmpp': 'hPa' }
if len(sys.argv) > 1:
    url = sys.argv[1]
    if not url.startswith('http'):
        url = 'http://' + url

logging.info(f"Using URL: {url}")

try:
    logging.info("sensors")

    epd = epd2in15g.EPD()   
    logging.info("init and Clear")
    epd.init()
    # epd.Clear()
    font15 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15)
    font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    font40 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 40)

    # Fetch sensor data
    logging.info("Fetching sensor data...")
    try:
        response = requests.get(url, timeout=10)
        response2 = requests.get(url2, timeout=10)
        response.raise_for_status()
        response2.raise_for_status()
        sensor_data_raw = response.text.strip()
        sensor_data_raw2 = response2.text.strip()
        logging.info(f"Raw sensor data: {sensor_data_raw}")
        logging.info(f"Raw sensor data: {sensor_data_raw2}")

        # Load cached sensor data
        cached_data = load_sensor_data()

        # Parse sensor data
        sensor_data = {}
        sensors_data_raw = sensor_data_raw + sensor_data_raw2
        pairs = sensors_data_raw.split(';')
        for pair in pairs:
            if ':' in pair:
                key, value = pair.split(':', 1)
                # Only process keys that have names and units defined
                if key in sensor_names and key in sensor_units:
                    show_value = value

                    # Use new value if it's valid, otherwise use cached value
                    if is_valid_value(show_value):
                        sensor_data[key] = { 'value': show_value, 'name': sensor_names[key], 'unit': sensor_units[key] }
                        logging.debug(f"Updated {key} with new value: {show_value}")
                    elif key in cached_data and 'value' in cached_data[key]:
                        # Use cached value if new value is invalid
                        cached_value = cached_data[key]['value']
                        sensor_data[key] = { 'value': cached_value, 'name': sensor_names[key], 'unit': sensor_units[key] }
                        logging.debug(f"Using cached value for {key}: {cached_value} (new value was: {show_value})")
                    else:
                        # No cached value available, use the invalid value anyway
                        sensor_data[key] = { 'value': show_value, 'name': sensor_names[key], 'unit': sensor_units[key] }
                        logging.debug(f"No cached value for {key}, using invalid value: {show_value}")

        # Save updated sensor data to file
        save_sensor_data(sensor_data)

        # Create display image
        Himage = Image.new('RGB', (epd.height, epd.width), epd.WHITE)
        draw = ImageDraw.Draw(Himage)

        # Display sensor data
        y_pos = 5
        draw.text((10, y_pos), 'Sensor Data', font=font40, fill=epd.BLACK)
        y_pos += 45

        # Display each sensor reading
        for key, value in sensor_data.items():
            if key in show_sensor_names:
                display_text = f"{value['name']}: {value['value']} {value['unit']}"
                draw.text((5, y_pos), display_text, font=font18, fill=epd.BLACK)
                y_pos += 24
            # If we run out of space, stop displaying
                if y_pos > epd.width - 30:
                    break

    except requests.RequestException as e:
        logging.error(f"Failed to fetch sensor data: {e}")
        # Load cached data as fallback
        cached_data = load_sensor_data()
        if cached_data:
            logging.info("Using cached sensor data")
            sensor_data = cached_data
            # Create display image with cached data
            Himage = Image.new('RGB', (epd.height, epd.width), epd.WHITE)
            draw = ImageDraw.Draw(Himage)

            # Display sensor data
            y_pos = 5
            draw.text((10, y_pos), 'Sensor Data (Cached)', font=font40, fill=epd.BLACK)
            y_pos += 45

            # Display each sensor reading
            for key, value in sensor_data.items():
                if key in show_sensor_names:
                    display_text = f"{value['name']}: {value['value']} {value['unit']}"
                    draw.text((5, y_pos), display_text, font=font18, fill=epd.YELLOW)  # Yellow for cached data
                    y_pos += 24
                # If we run out of space, stop displaying
                    if y_pos > epd.width - 30:
                        break
        else:
            # No cached data available, show error
            Himage = Image.new('RGB', (epd.height, epd.width), epd.WHITE)
            draw = ImageDraw.Draw(Himage)
            draw.text((10, 10), 'Error fetching sensor data', font=font24, fill=epd.RED)
            draw.text((10, 40), str(e), font=font18, fill=epd.BLACK)
            draw.text((10, 70), 'No cached data available', font=font18, fill=epd.BLACK)

    epd.display(epd.getbuffer(Himage))
    
    logging.info("Goto Sleep...")
    epd.sleep()

except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd2in15g.epdconfig.module_exit(cleanup=True)
    exit()
