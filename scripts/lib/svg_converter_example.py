#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Примеры использования модуля svg_converter для epd2in15g дисплея.
"""

import sys
import os
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd2in15g
from PIL import Image, ImageDraw
from svg_converter import example_to_image, svg_to_epd_image, list_examples, get_example_svg

logging.basicConfig(level=logging.INFO)

def example_1_basic_usage():
    """Пример 1: Базовое использование встроенных иконок"""
    print("Пример 1: Базовое использование встроенных иконок")
    
    epd = epd2in15g.EPD()
    epd.init()
    
    Himage = Image.new('RGB', (epd.height, epd.width), epd.WHITE)
    
    sun_icon = example_to_image('sun', epd, width=50, height=50)
    if sun_icon:
        Himage.paste(sun_icon, (10, 10))
    
    cloud_icon = example_to_image('cloud', epd, width=50, height=50)
    if cloud_icon:
        Himage.paste(cloud_icon, (70, 10))
    
    rain_icon = example_to_image('rain', epd, width=50, height=50)
    if rain_icon:
        Himage.paste(rain_icon, (130, 10))
    
    epd.display(epd.getbuffer(Himage))
    epd.sleep()


def example_2_custom_svg():
    """Пример 2: Использование собственного SVG"""
    print("Пример 2: Использование собственного SVG")
    
    custom_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" fill="#FF0000" stroke="#000000" stroke-width="2"/>
  <text x="50" y="55" font-family="Arial" font-size="30" text-anchor="middle" fill="white">!</text>
</svg>'''
    
    epd = epd2in15g.EPD()
    epd.init()
    
    Himage = Image.new('RGB', (epd.height, epd.width), epd.WHITE)
    
    custom_icon = svg_to_epd_image(custom_svg, epd, width=80, height=80)
    if custom_icon:
        Himage.paste(custom_icon, (100, 100))
    
    epd.display(epd.getbuffer(Himage))
    epd.sleep()


def example_3_all_examples():
    """Пример 3: Отображение всех доступных примеров"""
    print("Пример 3: Отображение всех доступных примеров")
    
    epd = epd2in15g.EPD()
    epd.init()
    
    Himage = Image.new('RGB', (epd.height, epd.width), epd.WHITE)
    draw = ImageDraw.Draw(Himage)
    
    examples = list_examples()
    x, y = 10, 10
    icon_size = 40
    spacing = 50
    
    for i, name in enumerate(examples):
        icon = example_to_image(name, epd, width=icon_size, height=icon_size)
        if icon:
            Himage.paste(icon, (x, y))
            draw.text((x, y + icon_size + 5), name[:8], fill=0)
        
        x += spacing
        if x + icon_size > epd.height:
            x = 10
            y += icon_size + 25
    
    epd.display(epd.getbuffer(Himage))
    epd.sleep()


def example_4_weather_icons():
    """Пример 4: Использование иконок погоды в контексте"""
    print("Пример 4: Использование иконок погоды в контексте")
    
    epd = epd2in15g.EPD()
    epd.init()
    
    Himage = Image.new('RGB', (epd.height, epd.width), epd.WHITE)
    draw = ImageDraw.Draw(Himage)
    
    weather_icons = {
        'sun': (10, 10),
        'cloud': (70, 10),
        'rain': (130, 10),
        'snow': (190, 10),
        'wind': (250, 10),
    }
    
    for icon_name, (x, y) in weather_icons.items():
        icon = example_to_image(icon_name, epd, width=40, height=40)
        if icon:
            Himage.paste(icon, (x, y))
    
    draw.text((10, 60), "Weather icons", epd.BLACK)
    
    epd.display(epd.getbuffer(Himage))
    epd.sleep()


def example_5_arrows_and_status():
    """Пример 5: Использование стрелок и статусных иконок"""
    print("Пример 5: Использование стрелок и статусных иконок")
    
    epd = epd2in15g.EPD()
    epd.init()
    
    Himage = Image.new('RGB', (epd.height, epd.width), epd.WHITE)
    draw = ImageDraw.Draw(Himage)
    
    arrow_up = example_to_image('arrow_up', epd, width=30, height=30)
    if arrow_up:
        Himage.paste(arrow_up, (10, 10))
    
    arrow_down = example_to_image('arrow_down', epd, width=30, height=30)
    if arrow_down:
        Himage.paste(arrow_down, (50, 10))
    
    check = example_to_image('check', epd, width=30, height=30)
    if check:
        Himage.paste(check, (90, 10))
    
    cross = example_to_image('cross', epd, width=30, height=30)
    if cross:
        Himage.paste(cross, (130, 10))
    
    wifi = example_to_image('wifi', epd, width=30, height=30)
    if wifi:
        Himage.paste(wifi, (170, 10))
    
    battery = example_to_image('battery', epd, width=40, height=20)
    if battery:
        Himage.paste(battery, (210, 15))
    
    draw.text((10, 50), "Стрелки и статусы", fill=0)
    
    epd.display(epd.getbuffer(Himage))
    epd.sleep()


if __name__ == '__main__':
    print("Доступные примеры:")
    print("  1. example_1_basic_usage() - Базовое использование")
    print("  2. example_2_custom_svg() - Собственный SVG")
    print("  3. example_3_all_examples() - Все примеры")
    print("  4. example_4_weather_icons() - Иконки погоды")
    print("  5. example_5_arrows_and_status() - Стрелки и статусы")
    print("\nДоступные встроенные SVG:")
    for name in list_examples():
        print(f"  - {name}")
    
    print("\nДля запуска примера используйте:")
    print("  python -c 'from lib.svg_converter_example import example_1_basic_usage; example_1_basic_usage()'")

