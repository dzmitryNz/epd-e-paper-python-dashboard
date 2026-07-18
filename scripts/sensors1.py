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

# Parse command line arguments
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

url = 'http://192.168.0.106/sensors'  # default URL
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
    epd.Clear()
    font15 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15)
    font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    font40 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 40)

    # Fetch sensor data
    logging.info("Fetching sensor data...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        sensor_data_raw = response.text.strip()
        logging.info(f"Raw sensor data: {sensor_data_raw}")

        # Parse sensor data
        sensor_data = {}
        pairs = sensor_data_raw.split(';')
        for pair in pairs:
            if ':' in pair:
                key, value = pair.split(':', 1)
                sensor_data[key] = value

        # Create display image
        Himage = Image.new('RGB', (epd.height, epd.width), epd.WHITE)
        draw = ImageDraw.Draw(Himage)

        # Display sensor data
        y_pos = 5
        draw.text((10, y_pos), 'Sensor Data', font=font40, fill=epd.BLACK)
        y_pos += 45

        # Display each sensor reading
        for key, value in sensor_data.items():
            display_text = f"{key}: {value}"
            draw.text((5, y_pos), display_text, font=font18, fill=epd.BLACK)
            y_pos += 24
            # If we run out of space, stop displaying
            if y_pos > epd.width - 30:
                break

    except requests.RequestException as e:
        logging.error(f"Failed to fetch sensor data: {e}")
        # Display error message
        Himage = Image.new('RGB', (epd.height, epd.width), epd.WHITE)
        draw = ImageDraw.Draw(Himage)
        draw.text((10, 10), 'Error fetching sensor data', font=font24, fill=epd.RED)
        draw.text((10, 40), str(e), font=font18, fill=epd.BLACK)

    epd.display(epd.getbuffer(Himage))
    
    logging.info("Goto Sleep...")
    epd.sleep()

except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd2in15g.epdconfig.module_exit(cleanup=True)
    exit()
