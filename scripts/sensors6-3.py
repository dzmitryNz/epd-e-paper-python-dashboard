#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd3in7
import time
from PIL import Image,ImageDraw,ImageFont
import requests
import json
import locale
import re

    # Try to set locale for date/time
try:
    locale.setlocale(locale.LC_TIME, 'be_BY.UTF-8')  # Belarusian
except locale.Error:
    locale.setlocale(locale.LC_TIME, '')  # System locale

# Parse command line arguments
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Sensor data file
SENSOR_DATA_FILE = 'sensor_data.json'
LINE_HEIGHT = 25
ALL_HEIGHT = 480
ALL_WIDTH = 280
X_POS = 0

# Verbs area constants
VERBS_UPDATE_INTERVAL = 300
VERBS_STATE_FILE = 'verbs_state.json'
VERBS_JSON_FILE = 'verbs.json'
VERBS_AREA_START_Y = None
VERBS_AREA_HEIGHT = None

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

def get_solopool_data():
    """Fetch solopool data from API"""
    try:
        response = requests.get(solopool_url, timeout=10)
        response.raise_for_status()
        solopool_data = response.json()
        stats = solopool_data.get('stats', {})

        solopool_info = {
            'hashrate': solopool_data.get('hashrate', 0),
            'luck': solopool_data.get('luck', 0),
            'blocks': stats.get('blocksFound', 0),
        }

        logging.info(f"Solopool data: {solopool_info}")
        return solopool_info
    except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
        logging.error(f"Failed to fetch solopool data: {e}")
        return None

def get_nano3stats_data():
    """Fetch nano3stats data from API"""
    try:
        cookies = {'auth': '13085de76207728e9bc1c222d0d08c22'}
        response = requests.get(nano3stats_url, cookies=cookies, timeout=10)
        response.raise_for_status()
        response_text = response.text.strip()
        print(response_text)
        start_marker = 'dashboardCallback('
        end_marker = ');'
        
        start_idx = response_text.find(start_marker)
        if start_idx != -1:
            json_start = start_idx + len(start_marker)
            end_idx = response_text.rfind(end_marker)
            if end_idx != -1:
                json_str = response_text[json_start:end_idx].strip()
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                nano3stats_data = json.loads(json_str)
                nano3stats_info = {
                    'workingmode': nano3stats_data.get('workingmode', '0'),
                    'workingstatus': nano3stats_data.get('workingstatus', '0'),
                    'power': nano3stats_data.get('power', '0'),
                }
                logging.info(f"Nano3stats data: {nano3stats_info}")
                return nano3stats_info
        
        logging.error(f"Unexpected response format from nano3stats: {response_text[:100]}")
        return None
    except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
        logging.error(f"Failed to fetch nano3stats data: {e}")
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

def load_verbs_data():
    """Load verbs data from static JSON file"""
    if os.path.exists(VERBS_JSON_FILE):
        try:
            with open(VERBS_JSON_FILE, 'r', encoding='utf-8') as f:
                verbs = json.load(f)
                logging.info(f"Loaded {len(verbs)} verbs from {VERBS_JSON_FILE}")
                return verbs
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Failed to load verbs from file: {e}")
    
    default_verbs = [
        {"infinitive": "go", "past": "went", "past_participle": "gone", "translation": "ісці"},
        {"infinitive": "see", "past": "saw", "past_participle": "seen", "translation": "бачыць"},
        {"infinitive": "come", "past": "came", "past_participle": "come", "translation": "прыходзіць"},
        {"infinitive": "know", "past": "knew", "past_participle": "known", "translation": "ведаць"},
        {"infinitive": "get", "past": "got", "past_participle": "got", "translation": "атрымліваць"}
    ]
    
    try:
        with open(VERBS_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_verbs, f, indent=2, ensure_ascii=False)
        logging.info(f"Created default verbs file {VERBS_JSON_FILE}")
    except IOError as e:
        logging.error(f"Failed to create verbs file: {e}")
    
    return default_verbs

def load_verbs_state():
    """Load verbs state from file"""
    if os.path.exists(VERBS_STATE_FILE):
        try:
            with open(VERBS_STATE_FILE, 'r') as f:
                state = json.load(f)
                logging.debug(f"Loaded verbs state: {state}")
                return state
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Failed to load verbs state from file: {e}")
    
    return {'current_page': 0, 'last_update_time': 0}

def save_verbs_state(state):
    """Save verbs state to file"""
    try:
        with open(VERBS_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        logging.debug(f"Saved verbs state to {VERBS_STATE_FILE}")
    except IOError as e:
        logging.error(f"Failed to save verbs state to file: {e}")

def calculate_verbs_per_page(font, line_height, max_height):
    """Calculate how many verbs fit on one page"""
    if max_height <= 0:
        return 0
    verbs_per_page = max_height // line_height
    return max(1, verbs_per_page)

def draw_verbs_section(draw, theme_config, verbs_list, current_page, y_pos, max_height):
    """Draw verbs section with pagination, descriptions and examples"""
    if not verbs_list or len(verbs_list) == 0:
        return y_pos
    
    font = theme_config['text_blocks']['description']['font']
    color = theme_config['text_blocks']['description']['color']
    unit_color = theme_config['text_blocks']['unit']['color']
    line_color = theme_config['text_blocks']['description']['color']
    
    draw.line([(X_POS, y_pos), (ALL_WIDTH, y_pos)], fill=line_color, width=1)
    y_pos += 3
    
    verbs_per_page = calculate_verbs_per_page(font, LINE_HEIGHT, max_height - 3)
    
    total_pages = (len(verbs_list) + verbs_per_page - 1) // verbs_per_page
    if total_pages == 0:
        return y_pos
    
    if current_page >= total_pages:
        current_page = 0
    
    start_idx = current_page * verbs_per_page
    end_idx = min(start_idx + verbs_per_page, len(verbs_list))
    page_verbs = verbs_list[start_idx:end_idx]
    
    max_infinitive_len = max(len(verb['infinitive']) for verb in page_verbs)
    max_past_len = max(len(verb['past']) for verb in page_verbs)
    max_participle_len = max(len(verb['past_participle']) for verb in page_verbs)
    
    if len(page_verbs) > 0 and 'translations' in page_verbs[0] and page_verbs[0]['translations']:
        trans = page_verbs[0]['translations']
        max_infinitive_len = max(max_infinitive_len, len(trans.get('infinitive', '')))
        max_past_len = max(max_past_len, len(trans.get('past', '')))
        max_participle_len = max(max_participle_len, len(trans.get('past_participle', '')))
    
    current_y = y_pos
    max_y = y_pos + max_height + 5
    
    for idx, verb in enumerate(page_verbs):
        if current_y + LINE_HEIGHT > max_y:
            break
        
        is_first_verb = (idx == 0)
        
        if is_first_verb and 'translations' in verb and verb['translations']:
            if current_y + LINE_HEIGHT - 5 > max_y:
                break
            trans = verb['translations']
            infinitive_trans = trans.get('infinitive', '')
            past_trans = trans.get('past', '')
            participle_trans = trans.get('past_participle', '')
            
            trans_text = f"{infinitive_trans:<{max_infinitive_len}} | {past_trans:<{max_past_len}} | {participle_trans:<{max_participle_len}}"
            draw.text((X_POS, current_y), trans_text, font=font, fill=unit_color)
            current_y += LINE_HEIGHT - 3
        
        infinitive = verb['infinitive']
        past = verb['past']
        participle = verb['past_participle']
        verb_text = f"{infinitive:<{max_infinitive_len}} | {past:<{max_past_len}} | {participle:<{max_participle_len}}"
        draw.text((X_POS, current_y), verb_text, font=font, fill=color)
        current_y += LINE_HEIGHT - 3
        
        if 'description' in verb and verb['description']:
            if current_y + LINE_HEIGHT - 5 > max_y:
                break
            desc_text = f"  {verb['description']}"
            draw.text((X_POS + 5, current_y), desc_text, font=font, fill=unit_color)
            current_y += LINE_HEIGHT - 5
        
        if 'examples' in verb and verb['examples'] and len(verb['examples']) > 0:
            if current_y + LINE_HEIGHT - 5 > max_y:
                break
            example = verb['examples'][0]
            verb_translation = ""
            if 'translation' in verb:
                verb_translation = verb['translation']
            
            max_total_len = 45
            if verb_translation:
                translation_len = min(len(verb_translation), 18)
                example_len = max_total_len - translation_len - 8
                if len(example) > example_len:
                    example = example[:example_len - 3] + "..."
                if len(verb_translation) > translation_len:
                    verb_translation = verb_translation[:translation_len - 3] + "..."
                example_text = f"{verb_translation} ex: {example}"
            else:
                if len(example) > max_total_len - 6:
                    example = example[:max_total_len - 9] + "..."
                example_text = f"ex: {example}"
            draw.text((X_POS + 5, current_y), example_text, font=font, fill=unit_color)
            current_y += LINE_HEIGHT - 5
        
        current_y += 2
    
    return current_y

def refresh_verbs_area(epd, theme_config, verbs_list, current_page, full_image, start_y, area_height):
    """Refresh verbs area in full image and return updated image"""
    draw = ImageDraw.Draw(full_image)
    
    background_color = theme_config['colors']['background']
    draw.rectangle([(X_POS, start_y), (ALL_WIDTH, start_y + area_height)], fill=background_color)
    
    draw_verbs_section(draw, theme_config, verbs_list, current_page, start_y, area_height)
    
    return full_image

def init_theme_config(epd, fonts):
    """Initialize theme configuration with colors, headers and text blocks"""
    font15, font18, font24, font40 = fonts
    
    theme_config = {
        'colors': {
            'background': epd.GRAY1,
            'header': epd.GRAY4,
            'primary_text': epd.GRAY4,
            'secondary_text': epd.GRAY4,
            'accent': epd.GRAY4
        },
        'headers': {
            'datetime': {'color': epd.GRAY4, 'font': font24},
            'section': {'color': epd.GRAY4, 'font': font18}
        },
        'text_blocks': {
            'label': {'color': epd.GRAY4, 'font': font18},
            'value': {'color': epd.GRAY4, 'font': font24},
            'value_small': {'color': epd.GRAY4, 'font': font18},
            'unit': {'color': epd.GRAY4, 'font': font18},
            'description': {'color': epd.GRAY4, 'font': font18},
            'crypto_up': {'color': epd.GRAY4, 'font': font18},
            'crypto_down': {'color': epd.GRAY4, 'font': font18}
        }
    }
    return theme_config

def collect_all_sensor_data(url, url2, weather_url, kucoin_url, kucoin_pairs, solopool_url, nano3stats_url, 
                            sensor_names, sensor_units, show_solopool_names, show_nano3stats_names,
                            solo_names, solo_units, nano3_names, nano3_units,
                            nano3_workingmodes, nano3_workingstatuses):
    """Collect all sensor data from different sources"""
    sensor_data = {}
    cached_data = load_sensor_data()
    
    try:
        response = requests.get(url, timeout=10)
        response2 = requests.get(url2, timeout=10)
        response.raise_for_status()
        response2.raise_for_status()
        sensor_data_raw = response.text.strip()
        sensor_data_raw2 = response2.text.strip()
        logging.info(f"Raw sensor data: {sensor_data_raw}")
        logging.info(f"Raw sensor data: {sensor_data_raw2}")
        
        sensors_data_raw = sensor_data_raw + sensor_data_raw2
        pairs = sensors_data_raw.split(';')
        for pair in pairs:
            if ':' in pair:
                key, value = pair.split(':', 1)
                if key in sensor_names and key in sensor_units:
                    show_value = value
                    if is_valid_value(show_value):
                        sensor_data[key] = {'value': show_value, 'name': sensor_names[key], 'unit': sensor_units[key]}
                        logging.debug(f"Updated {key} with new value: {show_value}")
                    elif key in cached_data and 'value' in cached_data[key]:
                        cached_value = cached_data[key]['value']
                        sensor_data[key] = {'value': cached_value, 'name': sensor_names[key], 'unit': sensor_units[key]}
                        logging.debug(f"Using cached value for {key}: {cached_value} (new value was: {show_value})")
                    else:
                        sensor_data[key] = {'value': show_value, 'name': sensor_names[key], 'unit': sensor_units[key]}
                        logging.debug(f"No cached value for {key}, using invalid value: {show_value}")
    except requests.RequestException as e:
        logging.error(f"Failed to fetch sensor data: {e}")
    
    weather_data = get_weather_data()
    kucoin_data = get_kucoin_data()
    solopool_data = get_solopool_data()
    nano3stats_data = get_nano3stats_data()
    
    if solopool_data:
        if 'hashrate' in show_solopool_names:
            sensor_data['hashrate'] = {
                'value': solopool_data['hashrate'],
                'name': solo_names['hashrate'],
                'unit': solo_units['hashrate']
            }
        if 'luck' in show_solopool_names:
            sensor_data['luck'] = {
                'value': solopool_data['luck'],
                'name': solo_names['luck'],
                'unit': solo_units['luck']
            }
        if 'blocks' in show_solopool_names:
            sensor_data['blocks'] = {
                'value': solopool_data['blocks'],
                'name': 'blocks',
                'unit': 'шт'
            }
    
    if nano3stats_data:
        if 'workingmode' in show_nano3stats_names:
            mode_value = nano3_workingmodes.get(nano3stats_data['workingmode'], nano3stats_data['workingmode'])
            sensor_data['workingmode'] = {
                'value': mode_value,
                'name': nano3_names['workingmode'],
                'unit': nano3_units['workingmode']
            }
        if 'workingstatus' in show_nano3stats_names:
            status_value = nano3_workingstatuses.get(nano3stats_data['workingstatus'], nano3stats_data['workingstatus'])
            sensor_data['workingstatus'] = {
                'value': status_value,
                'name': nano3_names['workingstatus'],
                'unit': nano3_units['workingstatus']
            }
        if 'power' in show_nano3stats_names:
            sensor_data['power'] = {
                'value': nano3stats_data['power'],
                'name': nano3_names['power'],
                'unit': nano3_units['power']
            }
    
    all_data = {
        'sensor_data': sensor_data,
        'weather_data': weather_data,
        'kucoin_data': kucoin_data
    }
    
    return all_data

def draw_datetime(draw, theme_config, y_pos):
    """Draw date and time"""
    datetime = time.strftime('%a - %d %b - %H:%M', time.localtime())
    header_style = theme_config['headers']['datetime']
    draw.text((X_POS, y_pos), datetime, font=header_style['font'], fill=header_style['color'])
    return y_pos + LINE_HEIGHT + 2

def draw_sun_info(draw, theme_config, weather_data, y_pos):
    """Draw sunrise/sunset information"""
    desc_style = theme_config['text_blocks']['description']
    if weather_data and 'sunrise' in weather_data and 'sunset' in weather_data:
        sunrise_time = format_sun_time(weather_data['sunrise'])
        sunset_time = format_sun_time(weather_data['sunset'])
        sun_info = f" ↑ {sunrise_time}  ↓ {sunset_time}   {weather_data['description']}"
        draw.text((X_POS, y_pos), sun_info, font=desc_style['font'], fill=desc_style['color'])
    else:
        header_style = theme_config['headers']['section']
        draw.text((X_POS, y_pos), "Sun times: N/A", font=header_style['font'], fill=header_style['color'])
    return y_pos + LINE_HEIGHT

def draw_weather_section(draw, theme_config, weather_data, sensor_data, y_pos, names, sensor_units, value_possitions, weather_possitions):
    """Draw weather and sensor data section"""
    if not weather_data:
        return y_pos
    
    label_style = theme_config['text_blocks']['label']
    value_style = theme_config['text_blocks']['value']
    value_small_style = theme_config['text_blocks']['value_small']
    unit_style = theme_config['text_blocks']['unit']
    desc_style = theme_config['text_blocks']['description']
    
    out_temp = sensor_data.get('dsw1', {}).get('value', 'N/A')
    bal_temp = sensor_data.get('dsw2', {}).get('value', 'N/A')
    bk_temp = sensor_data.get('bmpt', {}).get('value', 'N/A')
    press_sensor = sensor_data.get('bmpp', {}).get('value', 'N/A')
    
    draw.text((X_POS, y_pos), f"{names['dsw1']}, {sensor_units['dsw1']}:", font=label_style['font'], fill=label_style['color'])
    draw.text((value_possitions['dsw1'], y_pos - 4), f"{out_temp}", font=value_style['font'], fill=value_style['color'])
    draw.text((weather_possitions['dsw1'], y_pos), f" {names['feels']} {weather_data['feels_like']} - {weather_data['temp']}", font=desc_style['font'], fill=desc_style['color'])
    y_pos += LINE_HEIGHT
    
    draw.text((X_POS, y_pos), f"{names['humidity']}, {sensor_units['humidity']}:", font=label_style['font'], fill=label_style['color'])
    draw.text((weather_possitions['humidity'], y_pos - 4), f"{weather_data['humidity']}", font=value_style['font'], fill=value_style['color'])
    draw.text((weather_possitions['wind_speed'], y_pos), f"{names['wind_speed']} {get_wind_direction(weather_data['wind_deg'])}, {weather_data['wind_speed']}  {sensor_units['wind_speed']}", font=desc_style['font'], fill=desc_style['color'])
    y_pos += LINE_HEIGHT
    
    draw.text((X_POS, y_pos), f"{names['bmpp']}, {sensor_units['bmpp']}:", font=label_style['font'], fill=label_style['color'])
    draw.text((value_possitions['bmpp'], y_pos - 4), f"{press_sensor}", font=value_style['font'], fill=value_style['color'])
    draw.text((weather_possitions['pressure'], y_pos), f"{names['clouds']} {weather_data['clouds']} {sensor_units['clouds']}", font=desc_style['font'], fill=desc_style['color'])
    y_pos += LINE_HEIGHT - 2
    
    draw.text((X_POS, y_pos), f"{names['bl']}, {sensor_units['dsw2']}:", font=label_style['font'], fill=label_style['color'])
    draw.text((value_possitions['dsw2'], y_pos), f"{bal_temp}", font=value_small_style['font'], fill=value_small_style['color'])
    draw.text((value_possitions['bmpt'], y_pos), f"{names['bk']}, {sensor_units['bmpt']}:", font=label_style['font'], fill=label_style['color'])
    draw.text((value_possitions['bmpt'] + 60, y_pos), f"{bk_temp}", font=value_small_style['font'], fill=value_small_style['color'])
    y_pos += LINE_HEIGHT - 2
    
    return y_pos

def draw_crypto_section(draw, theme_config, kucoin_data, y_pos, kucoin_pairs):
    """Draw cryptocurrency prices section"""
    label_style = theme_config['text_blocks']['label']
    crypto_up_style = theme_config['text_blocks']['crypto_up']
    crypto_down_style = theme_config['text_blocks']['crypto_down']
    
    if kucoin_data:
        pair1 = kucoin_pairs[0] if len(kucoin_pairs) > 0 else None
        pair2 = kucoin_pairs[1] if len(kucoin_pairs) > 1 else None
        pair3 = kucoin_pairs[2] if len(kucoin_pairs) > 2 else None
        
        x_pos = X_POS
        if pair1 and pair1 in kucoin_data:
            price1 = round(float(kucoin_data[pair1]['last']))
            change_rate1 = float(kucoin_data[pair1]['change_rate']) * 100
            color1_style = crypto_down_style if change_rate1 < 0 else crypto_up_style
            draw.text((x_pos, y_pos), f"{pair1.split('-')[0]}", font=label_style['font'], fill=label_style['color'])
            x_pos += 32
            draw.text((x_pos, y_pos), f"${price1}", font=color1_style['font'], fill=color1_style['color'])
            x_pos += 75
        
        if pair2 and pair2 in kucoin_data:
            price2 = round(float(kucoin_data[pair2]['last']))
            change_rate2 = float(kucoin_data[pair2]['change_rate']) * 100
            color2_style = crypto_down_style if change_rate2 < 0 else crypto_up_style
            draw.text((x_pos, y_pos), f"{pair2.split('-')[0]}", font=label_style['font'], fill=label_style['color'])
            x_pos += 32
            draw.text((x_pos, y_pos), f"${price2}", font=color2_style['font'], fill=color2_style['color'])
            x_pos += 45
        
        if pair3 and pair3 in kucoin_data:
            price3 = round(float(kucoin_data[pair3]['last']), 2)
            change_rate3 = float(kucoin_data[pair3]['change_rate']) * 100
            color3_style = crypto_down_style if change_rate3 < 0 else crypto_up_style
            draw.text((x_pos, y_pos), f"{pair3.split('-')[0]}", font=label_style['font'], fill=label_style['color'])
            x_pos += 41
            draw.text((x_pos, y_pos), f"${price3}", font=color3_style['font'], fill=color3_style['color'])
    else:
        desc_style = theme_config['text_blocks']['description']
        draw.text((X_POS, y_pos), "Crypto: N/A", font=desc_style['font'], fill=desc_style['color'])
    
    return y_pos + LINE_HEIGHT - 2

def draw_mining_section(draw, theme_config, sensor_data, y_pos, solo_names, solo_units, nano3_names):
    """Draw solopool and nano3stats mining data section"""
    desc_style = theme_config['text_blocks']['description']
    
    hashrate_value = sensor_data.get('hashrate', {}).get('value', 'N/A')
    luck_value = sensor_data.get('luck', {}).get('value', 'N/A')
    blocks_value = sensor_data.get('blocks', {}).get('value', 'N/A')
    if hashrate_value != 'N/A':
        hashrate_formatted = f"{hashrate_value / 1e12:.2f}T" if hashrate_value >= 1e12 else f"{hashrate_value / 1e9:.2f}G" if hashrate_value >= 1e9 else f"{hashrate_value / 1e6:.2f}M"
    else:
        hashrate_formatted = 'N/A'
    
    workingmode_value = sensor_data.get('workingmode', {}).get('value', 'N/A')
    workingstatus_value = sensor_data.get('workingstatus', {}).get('value', 'Err')
    power_value = sensor_data.get('power', {}).get('value', 'N/A')
    power_unit = sensor_data.get('power', {}).get('unit', '')
    
    solopool_text = f"{blocks_value} {solo_names['hashrate']} {hashrate_formatted}{solo_units['hashrate']} {luck_value} {solo_units['luck']}"
    nano3_text = f" {nano3_names['workingmode']} {workingmode_value} {nano3_names['workingstatus']} {workingstatus_value} {nano3_names['power']} {power_value}{power_unit}"
    draw.text((0, y_pos), f"{solopool_text}{nano3_text}", font=desc_style['font'], fill=desc_style['color'])
    
    return y_pos

def draw_all(draw, theme_config, all_data, names, sensor_units, value_possitions, weather_possitions, 
             kucoin_pairs, solo_names, solo_units, nano3_names, verbs_list=None, current_page=0):
    """Main drawing function that coordinates all drawing functions"""
    y_pos = 0
    y_pos = draw_datetime(draw, theme_config, y_pos)
    y_pos = draw_sun_info(draw, theme_config, all_data['weather_data'], y_pos)
    y_pos = draw_weather_section(draw, theme_config, all_data['weather_data'], all_data['sensor_data'], 
                                  y_pos, names, sensor_units, value_possitions, weather_possitions)
    y_pos = draw_crypto_section(draw, theme_config, all_data['kucoin_data'], y_pos, kucoin_pairs)
    y_pos = draw_mining_section(draw, theme_config, all_data['sensor_data'], y_pos, 
                                solo_names, solo_units, nano3_names)
    
    verbs_start_y = y_pos + LINE_HEIGHT
    verbs_area_height = ALL_HEIGHT - verbs_start_y
    
    if verbs_list and len(verbs_list) > 0:
        y_pos = draw_verbs_section(draw, theme_config, verbs_list, current_page, verbs_start_y, verbs_area_height)
    
    return y_pos, verbs_start_y, verbs_area_height

url = 'http://192.168.0.106/sensors'  # default URL
url2 = 'http://192.168.0.100/sensors'  # default URL
weather_url = 'https://api.openweathermap.org/data/2.5/weather?q=Mogilev&lang=be&appid=351bef36095247499eb96265dfb607d2&units=metric'
icons_path = './icons/'
kucoin_url = 'https://api.kucoin.com/api/v1/market/allTickers'
kucoin_pairs = ['BTC-USDC', 'LTC-USDC', 'LINK-USDC']
solopool_url = 'https://fb.solopool.org/api/accounts/bc1q5wvu30rmag0xv2s046wksxzt5grqggzhapugjy'
nano3stats_url = 'http://192.168.0.248/get_dashboard.cgi'

show_sensor_names = ['dsw1', 'dsw2', 'bmpt', 'bmpp']
show_solopool_names = ['hashrate', 'luck', 'blocks']
show_nano3stats_names = ['workingmode', 'workingstatus', 'power']
nano3_workingmodes = { '0': 'Lo', '1': 'Mi', '2': 'Hi' }
nano3_workingstatuses = { '0': 'Init', '1': 'Fine', '2': 'Idle' }

sensor_names = { 'dsw1': 'Нар', 'dsw2': 'Bal', 'bmpt': 'BK', 'bmpp': 'Prs' }
sensor_units = { 'dsw1': '°C', 'dsw2': '°C', 'bmpt': '°C', 'bmpp': 'hPa', 'humidity': '%', 'wind_speed': 'мс', 'clouds': '%' }
value_possitions = { 'dsw1': 70, 'dsw2': 70, 'bmpt': 120, 'bmpp': 85 }
weather_possitions = { 'dsw1': 120, 'humidity': 75,'wind_speed': 120, 'pressure': 170, 'description': 120 }
names = { 'dsw1': 'Out', 'feels': 'Адчув.', 'humidity': 'Вільг', 'wind_speed': 'Вецер', 'bmpp': 'Ціск', 'clouds': 'Вобл', 'bl': 'Бал', 'bk': 'ВК'  }
solo_names = { 'hashrate': 'FB', 'luck': 'Уд', }
solo_units = { 'hashrate': 'H/s', 'luck': '%' }
nano3_names = { 'workingmode': '', 'workingstatus': '', 'power': '' }
nano3_units = { 'workingmode': '', 'workingstatus': '', 'power': 'W' }

if len(sys.argv) > 1:
    url = sys.argv[1]
    if not url.startswith('http'):
        url = 'http://' + url

logging.info(f"Using URL: {url}")

try:
    logging.info("sensors")

    needs_full_refresh = True

    epd = epd3in7.EPD()
    logging.info("init and Clear")
    epd.init(0)

    font15 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15)
    font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    font40 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 40)

    theme_config = init_theme_config(epd, (font15, font18, font24, font40))

    verbs_list = load_verbs_data()
    verbs_state = load_verbs_state()
    current_page = verbs_state.get('current_page', 0)
    last_verbs_update = verbs_state.get('last_update_time', 0)
    current_time = time.time()

    logging.info("Fetching sensor data...")
    all_data = collect_all_sensor_data(
        url, url2, weather_url, kucoin_url, kucoin_pairs, solopool_url, nano3stats_url,
        sensor_names, sensor_units, show_solopool_names, show_nano3stats_names,
        solo_names, solo_units, nano3_names, nano3_units,
        nano3_workingmodes, nano3_workingstatuses
    )

    sensor_data = all_data['sensor_data']
    previous_data = load_sensor_data()
    needs_full_refresh = data_changed_significantly(sensor_data, previous_data)
    save_sensor_data(sensor_data)

    Himage = Image.new('L', (epd.width, epd.height), theme_config['colors']['background'])
    draw = ImageDraw.Draw(Himage)

    y_pos, verbs_start_y, verbs_area_height = draw_all(draw, theme_config, all_data, names, sensor_units, value_possitions, weather_possitions,
             kucoin_pairs, solo_names, solo_units, nano3_names, verbs_list, current_page)

    VERBS_AREA_START_Y = verbs_start_y
    VERBS_AREA_HEIGHT = verbs_area_height

    if needs_full_refresh:
        logging.info("Display refresh: significant data change detected")
    else:
        logging.info("Display refresh: minor data change (using same refresh method)")

    epd.display_4Gray(epd.getbuffer_4Gray(Himage))
    
    saved_image_path = 'saved_display_image.png'
    Himage.save(saved_image_path)
    logging.info(f"Saved display image to {saved_image_path}")

    time_since_last_update = current_time - last_verbs_update
    if time_since_last_update >= VERBS_UPDATE_INTERVAL:
        logging.info(f"Time to update verbs: {time_since_last_update} seconds passed")
        
        verbs_per_page = calculate_verbs_per_page(font15, LINE_HEIGHT, verbs_area_height)
        total_pages = (len(verbs_list) + verbs_per_page - 1) // verbs_per_page if verbs_list and len(verbs_list) > 0 else 0
        
        if total_pages > 0:
            current_page = (current_page + 1) % total_pages
            logging.info(f"Switching to verbs page {current_page + 1}/{total_pages}")
            
            if os.path.exists(saved_image_path):
                try:
                    Himage = Image.open(saved_image_path).convert('L')
                except Exception as e:
                    logging.warning(f"Failed to load saved image: {e}, creating new one")
                    Himage = Image.new('L', (epd.width, epd.height), theme_config['colors']['background'])
            else:
                Himage = Image.new('L', (epd.width, epd.height), theme_config['colors']['background'])
            
            Himage = refresh_verbs_area(epd, theme_config, verbs_list, current_page, Himage, verbs_start_y, verbs_area_height)
            
            epd.display_4Gray(epd.getbuffer_4Gray(Himage))
            Himage.save(saved_image_path)
            
            verbs_state['current_page'] = current_page
            verbs_state['last_update_time'] = current_time
            save_verbs_state(verbs_state)
            logging.info(f"Updated verbs area and saved state")
        else:
            logging.warning("No verbs to display")
    
    logging.info("Goto Sleep...")
    epd.sleep()

except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd3in7.epdconfig.module_exit(cleanup=True)
    exit()
