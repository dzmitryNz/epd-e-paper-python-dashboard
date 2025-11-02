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

def format_sun_time(timestamp):
    """Format unix timestamp to HH:MM format"""
    return time.strftime('%H:%M', time.localtime(timestamp))

def get_weather_data():
    """Fetch weather data from OpenWeatherMap API"""
    try:
        response = requests.get(weather_url, timeout=10)
        response.raise_for_status()
        weather_data = response.json()

        # Extract relevant weather information
        weather_info = {
            'temp': round(weather_data['main']['temp'], 1),
            'feels_like': round(weather_data['main']['feels_like'], 1),
            'humidity': weather_data['main']['humidity'],
            'pressure': weather_data['main']['pressure'],
            'wind_speed': round(weather_data['wind']['speed'], 1),
            'wind_deg': weather_data['wind']['deg'],
            'clouds': weather_data['clouds']['all'],
            'description': weather_data['weather'][0]['description'],
            'city': weather_data['name'],
            'sunrise': weather_data['sys']['sunrise'],
            'sunset': weather_data['sys']['sunset']
        }
        logging.info(f"Weather data: {weather_info}")
        return weather_info
    except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
        logging.error(f"Failed to fetch weather data: {e}")
        return None

def get_kucoin_data():
    """Fetch cryptocurrency prices from KuCoin API"""
    try:
        response = requests.get(kucoin_url, timeout=10)
        response.raise_for_status()
        kucoin_data = response.json()

        if kucoin_data.get('code') != '200000':
            logging.error(f"KuCoin API error: {kucoin_data.get('msg', 'Unknown error')}")
            return None

        # Extract prices for specified pairs
        prices = {}
        ticker_data = kucoin_data.get('data', {}).get('ticker', [])

        for ticker in ticker_data:
            symbol = ticker.get('symbol')
            if symbol in kucoin_pairs:
                prices[symbol] = {
                    'last': ticker.get('last'),
                    'change_rate': ticker.get('changeRate'),
                    'change_price': ticker.get('changePrice')
                }

        logging.info(f"KuCoin prices: {prices}")
        return prices
    except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
        logging.error(f"Failed to fetch KuCoin data: {e}")
        return None

def data_changed_significantly(new_data, old_data):
    """
    Check if sensor data changed significantly enough to warrant logging.
    Uses different thresholds for different sensor types.
    """
    if not old_data:
        return True  # No old data = significant change

    for key in new_data:
        if key not in old_data:
            continue

        try:
            new_val = float(new_data[key]['value'])
            old_val = float(old_data[key]['value'])

            if old_val == 0:
                if new_val != 0:
                    return True  # Changed from 0 to non-zero
            else:
                if old_val != new_val:
                    logging.debug(f"Significant change in {key}: {old_val} -> {new_val}")
                    return True
        except (ValueError, KeyError):
            # If we can't compare values, consider it a change
            if new_data[key]['value'] != old_data[key]['value']:
                return True

    return False

def get_wind_direction(wind_deg):
    """Convert wind direction in degrees to text"""
    directions = ['С', 'СВ', 'В', 'ЮВ', 'Ю', 'ЮЗ', 'З', 'СЗ']
    return directions[int((wind_deg / 45) + 0.5)]

url = 'http://192.168.0.106/sensors'  # default URL
url2 = 'http://192.168.0.100/sensors'  # default URL
weather_url = 'https://api.openweathermap.org/data/2.5/weather?q=Mogilev&lang=be&appid=351bef36095247499eb96265dfb607d2&units=metric'
icons_path = './icons/'
kucoin_url = 'https://api.kucoin.com/api/v1/market/allTickers'
kucoin_pairs = ['BTC-USDC', 'LTC-USDC', 'LINK-USDC', 'SOL-USDC']

show_sensor_names = ['dsw1', 'dsw2', 'bmpt', 'bmpp']
sensor_names = { 'dsw1': 'Out', 'dsw2': 'Bal', 'bmpt': 'BK', 'bmpp': 'Prs' }
sensor_units = { 'dsw1': '°C', 'dsw2': '°C', 'bmpt': '°C', 'bmpp': 'hPa' }
value_possitions = { 'dsw1': 80, 'dsw2': 70, 'bmpt': 120, 'bmpp': 95 }
weather_possitions = { 'dsw1': 120, 'humidity': 80,'wind_speed': 110, 'pressure': 170, 'description': 120 }

br = 22
epaper = []

font15 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15)
font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)
font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
font40 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 40)

try:
    logging.info("sensors")

    # Initialize refresh type flag
    needs_full_refresh = True  # Default to full refresh

    epd = epd2in15g.EPD()
    logging.info("init and Clear")
    epd.init()
    # epd.Clear()

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

        # Fetch weather data
        weather_data = get_weather_data()

        # Fetch KuCoin prices
        kucoin_data = get_kucoin_data()

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

        # Check if we need full or partial refresh
        previous_data = load_sensor_data()

        # Determine if data changed significantly (using sensor-specific thresholds)
        needs_full_refresh = data_changed_significantly(sensor_data, previous_data)

        # Save updated sensor data to file
        save_sensor_data(sensor_data)

        # Create display image
        Himage = Image.new('RGB', (epd.height, epd.width), epd.WHITE)
        draw = ImageDraw.Draw(Himage)

        # Display date/time
        y_pos = 0
        datetime = time.strftime('%a - %d %b - %H:%M', time.localtime())
        draw.text((5, y_pos), datetime, font=font24, fill=epd.RED)
        y_pos += 25

        # Display sunrise/sunset information
        if weather_data and 'sunrise' in weather_data and 'sunset' in weather_data:
            sunrise_time = format_sun_time(weather_data['sunrise'])
            sunset_time = format_sun_time(weather_data['sunset'])
            sun_info = f" ↑ {sunrise_time}       ↓ {sunset_time}   {weather_data['description']}"
            draw.text((5, y_pos), sun_info, font=font18, fill=epd.BLACK)
        else:
            draw.text((5, y_pos), "Sun times: N/A", font=font18, fill=epd.RED)
        y_pos += br

        # Display weather and sensor data in the requested format
        if weather_data:
            # Get sensor values for display
            out_temp = sensor_data.get('dsw1', {}).get('value', 'N/A')
            bal_temp = sensor_data.get('dsw2', {}).get('value', 'N/A')
            bk_temp = sensor_data.get('bmpt', {}).get('value', 'N/A')
            press_sensor = sensor_data.get('bmpp', {}).get('value', 'N/A')

            # Line 3: Out temperature + weather temperature with feels
            draw.text((5, y_pos), f"Out, °C:", font=font18, fill=epd.BLACK)
            draw.text((value_possitions['dsw1'], y_pos - 4), f"{out_temp}", font=font24, fill=epd.RED)
            draw.text((weather_possitions['dsw1'], y_pos), f" feels {weather_data['feels_like']} - {weather_data['temp']}", font=font18, fill=epd.BLACK)
            y_pos += br

            # Line 4: Humidity + Wind + Description
            draw.text((5, y_pos), f"Hum, %:", font=font18, fill=epd.YELLOW)
            draw.text((weather_possitions['humidity'], y_pos), f"{weather_data['humidity']}", font=font18, fill=epd.BLACK)
            draw.text((weather_possitions['wind_speed'], y_pos), f"Wind, ms: {weather_data['wind_speed']}  {get_wind_direction(weather_data['wind_deg'])}", font=font18, fill=epd.BLACK)
            y_pos += br

            # Line 5: Sensor pressure + Weather pressure
            draw.text((5, y_pos), f"Press, hPa:", font=font18, fill=epd.BLACK)
            draw.text((value_possitions['bmpp'], y_pos - 4), f"{press_sensor}", font=font24, fill=epd.RED)
            draw.text((weather_possitions['pressure'], y_pos), f"Вобл, %: {weather_data['clouds']}", font=font18, fill=epd.BLACK)
            y_pos += br

            # Line 6: Balcony and BK temperatures
            draw.text((5, y_pos), f"Bal, °C:", font=font18, fill=epd.BLACK)
            draw.text((value_possitions['dsw2'], y_pos), f"{bal_temp}", font=font18, fill=epd.RED)
            draw.text((value_possitions['bmpt'], y_pos), f"BK, °C:", font=font18, fill=epd.BLACK)
            draw.text((value_possitions['bmpt'] + 60, y_pos), f"{bk_temp}", font=font18, fill=epd.RED)
            y_pos += br

            # Line 7: Kucoin prices
            if kucoin_data:
                # Display up to 2 pairs on this line due to space constraints
                pair1 = kucoin_pairs[0] if len(kucoin_pairs) > 0 else None
                pair2 = kucoin_pairs[1] if len(kucoin_pairs) > 1 else None
                pair3 = kucoin_pairs[2] if len(kucoin_pairs) > 2 else None

                x_pos = 5
                if pair1 and pair1 in kucoin_data:
                    price1 = round(float(kucoin_data[pair1]['last']))
                    change_rate1 = float(kucoin_data[pair1]['change_rate']) * 100
                    color1 = epd.RED if change_rate1 < 0 else epd.BLACK
                    draw.text((x_pos, y_pos), f"{pair1.split('-')[0]}:", font=font18, fill=epd.BLACK)
                    x_pos += 35
                    draw.text((x_pos, y_pos), f"${price1}", font=font18, fill=color1)
                    x_pos += 75

                if pair2 and pair2 in kucoin_data:
                    price2 = round(float(kucoin_data[pair2]['last']))
                    change_rate2 = float(kucoin_data[pair2]['change_rate']) * 100
                    color2 = epd.RED if change_rate2 < 0 else epd.BLACK
                    draw.text((x_pos, y_pos), f"{pair2.split('-')[0]}:", font=font18, fill=epd.BLACK)
                    x_pos += 35
                    draw.text((x_pos, y_pos), f"${price2}", font=font18, fill=color2)
                    x_pos += 50

                if pair3 and pair3 in kucoin_data:
                    price3 = round(float(kucoin_data[pair3]['last']), 2)
                    change_rate3 = float(kucoin_data[pair3]['change_rate']) * 100
                    color3 = epd.RED if change_rate3 < 0 else epd.BLACK
                    draw.text((x_pos, y_pos), f"{pair3.split('-')[0]}:", font=font18, fill=epd.BLACK)
                    x_pos += 40
                    draw.text((x_pos, y_pos), f"${price3}", font=font18, fill=color3)
            else:
                draw.text((5, y_pos), "Crypto: Offline", font=font18, fill=epd.RED)
            y_pos += br
        else:
            # Fallback when no weather data
            draw.text((5, y_pos), "Weather: Offline", font=font18, fill=epd.RED)
            y_pos += br

            # Still show sensor data
            for key, value in sensor_data.items():
                if key in show_sensor_names:
                    display_text = f"{value['name']}: {value['value']} {value['unit']}"
                    draw.text((5, y_pos), display_text, font=font18, fill=epd.YELLOW)
                    y_pos += br
                    if y_pos > epd.width - 30:
                        break

    except requests.RequestException as e:
        logging.error(f"Failed to fetch sensor data: {e}")

    logging.info("Goto Sleep...")
    epd.sleep()

except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd2in15g.epdconfig.module_exit(cleanup=True)
    exit()