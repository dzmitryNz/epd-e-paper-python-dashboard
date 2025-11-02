#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import sys
import time
import logging
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Optional, Tuple

iconsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'icons')
fontsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fonts')
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in15g
from config_loader import get_display_colour

class DisplayRenderer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.epd_type = config['display']['epdDisplayType']
        self.epd = epd2in15g.EPD()
        self.old_data_colour = config['display'].get('oldDataColour', 'YELLOW')
        self.rotation = config['display'].get('epdDisplayRotation', 0)
        
        self.fonts = self._load_fonts()
        self.line_height = config['layout'].get('lineHeight', 22)
        self.start_x = config['layout'].get('startX', 5)
        
        if self.rotation in [90, 270]:
            self.image_width = self.epd.height
            self.image_height = self.epd.width
        else:
            self.image_width = self.epd.width
            self.image_height = self.epd.height
        
    def _load_fonts(self) -> Dict[str, ImageFont.FreeTypeFont]:
        """Loads fonts from configuration"""
        fonts = {}
        fonts_config = self.config.get('fonts', {})
        
        for font_name, font_config in fonts_config.items():
            font_file, font_size = font_config
            font_path = os.path.join(fontsdir, font_file)
            try:
                fonts[font_name] = ImageFont.truetype(font_path, font_size)
            except Exception as e:
                logging.warning(f"Failed to load font {font_name}: {e}")
                fonts[font_name] = ImageFont.load_default()
        
        return fonts
    
    def _get_colour(self, colour_name: str, is_old_data: bool = False) -> Any:
        """Gets color for display"""
        if is_old_data:
            colour_name = self.old_data_colour
        
        epd_colour_map = {
            'BLACK': self.epd.BLACK,
            'WHITE': self.epd.WHITE,
            'RED': self.epd.RED,
            'YELLOW': self.epd.YELLOW
        }
        
        return epd_colour_map.get(colour_name, self.epd.BLACK)
    
    def _format_datetime(self, fmt: str) -> str:
        """Formats current date and time"""
        return time.strftime(fmt, time.localtime())
    
    def _format_sun_time(self, timestamp: int, fmt: str) -> str:
        """Formats sunrise/sunset time"""
        return time.strftime(fmt, time.localtime(timestamp))
    
    def _get_wind_direction(self, wind_deg: int) -> str:
        """Converts wind direction in degrees to text"""
        directions = ['С', 'СВ', 'В', 'ЮВ', 'Ю', 'ЮЗ', 'З', 'СЗ']
        return directions[int((wind_deg / 45) + 0.5) % 8]
    
    def _get_value(self, data: Dict[str, Any], data_ages: Dict[str, Dict[str, bool]], 
                   item_type: str, category: str = 'sensors') -> Tuple[Any, bool]:
        """Gets value from data and flag indicating if it's old"""
        category_data = data.get(category, {})
        
        if category == 'weather':
            if item_type == 'wind_direction' and 'wind_deg' in category_data:
                value = self._get_wind_direction(category_data['wind_deg'])
                is_old = data_ages.get(category, {}).get('wind_deg', False)
            else:
                value = category_data.get(item_type)
                is_old = data_ages.get(category, {}).get(item_type, False)
        elif category == 'kucoin':
            pair_data = category_data.get(item_type, {})
            value = pair_data.get('last') if isinstance(pair_data, dict) else None
            is_old = data_ages.get(category, {}).get(item_type, False)
        else:
            value = category_data.get(item_type)
            is_old = data_ages.get(category, {}).get(item_type, False)
        
        if value is None:
            value = 'N/A'
        
        return value, is_old
    
    def _format_value(self, value: Any, item_config: Dict[str, Any]) -> str:
        """Formats value for display"""
        if value is None or value == 'N/A':
            prefix = item_config.get('prefix', '')
            return f"{prefix}N/A".strip()
        
        prefix = item_config.get('prefix', '')
        suffix = item_config.get('suffix', '')
        
        if isinstance(value, (int, float)):
            if isinstance(value, float) and value == int(value):
                value_str = str(int(value))
            elif isinstance(value, float):
                value_str = f"{value:.2f}"
            else:
                value_str = str(value)
            return f"{prefix}{value_str}{suffix}".strip()
        
        return f"{prefix}{value}{suffix}".strip()
    
    def render(self, data: Dict[str, Any], data_ages: Dict[str, Dict[str, bool]]) -> Image.Image:
        """Renders all data on image"""
        
        image = Image.new('RGB', (self.image_width, self.image_height), self.epd.WHITE)
        draw = ImageDraw.Draw(image)
        
        y_pos = 0
        lines = self.config['dashboard'].get('lines', [])
        
        for line_config in lines:
            line_start_y = line_config.get('startY', y_pos)
            if line_start_y >= 0:
                y_pos = line_start_y
            
            line_start_x = line_config.get('startX', self.start_x)
            x_pos = line_start_x
            
            items = line_config.get('items', [])
            
            for item_config in items:
                item_type = item_config.get('type')
                item_x = item_config.get('startY', 0)
                if item_x > 0:
                    x_pos = line_start_x + item_x
                
                font_name = item_config.get('font', 'font18')
                font = self.fonts.get(font_name, self.fonts.get('font18'))
                colour_name = item_config.get('colour', 'BLACK')
                
                if item_type == 'datetime':
                    value = self._format_datetime(item_config.get('format', '%a - %d %b - %H:%M'))
                    is_old = False
                elif item_type == 'sunrise':
                    value, is_old = self._get_value(data, data_ages, 'sunrise', 'weather')
                    if value and value != 'N/A':
                        value = self._format_sun_time(value, item_config.get('format', '%H:%M'))
                elif item_type == 'sunset':
                    value, is_old = self._get_value(data, data_ages, 'sunset', 'weather')
                    if value and value != 'N/A':
                        value = self._format_sun_time(value, item_config.get('format', '%H:%M'))
                elif item_type in ['dsw1', 'dsw2', 'bmpt', 'bmpp']:
                    value, is_old = self._get_value(data, data_ages, item_type, 'sensors')
                elif item_type in ['temp', 'feels_like', 'humidity', 'pressure', 'wind_speed', 
                                   'wind_direction', 'clouds', 'description']:
                    value, is_old = self._get_value(data, data_ages, item_type, 'weather')
                elif item_type.endswith('-USDC') or item_type in ['BTC-USDC', 'LTC-USDC', 'LINK-USDC', 'SOL-USDC']:
                    value, is_old = self._get_value(data, data_ages, item_type, 'kucoin')
                    if value and value != 'N/A' and isinstance(value, (int, float)):
                        value = f"${value}"
                else:
                    value = 'N/A'
                    is_old = False
                
                display_text = self._format_value(value, item_config)
                colour = self._get_colour(colour_name, is_old)
                
                draw.text((x_pos, y_pos), display_text, font=font, fill=colour)
                
                after_x = item_config.get('afterX', 0)
                try:
                    bbox = font.getbbox(display_text)
                    text_width = bbox[2] - bbox[0]
                except AttributeError:
                    text_width = font.getsize(display_text)[0]
                x_pos += text_width + after_x
            
            after_y = line_config.get('afterY', self.line_height)
            y_pos += after_y
            
            if y_pos > self.image_height - 30:
                break
        
        if self.rotation != 0:
            image = image.rotate(-self.rotation, expand=True, fillcolor=self.epd.WHITE)
        
        return image
    
    def init_display(self):
        """Initializes display"""
        logging.info("Initializing display")
        self.epd.init()
    
    def display_image(self, image: Image.Image, full_refresh: bool = True):
        """Displays image on display"""
        if full_refresh:
            self.epd.Clear()
        
        try:
            self.epd.display(self.epd.getbuffer(image))
        except AttributeError:
            self.epd.Display(self.epd.getbuffer(image))
    
    def sleep(self):
        """Puts display to sleep mode"""
        logging.info("Going to sleep...")
        self.epd.sleep()

