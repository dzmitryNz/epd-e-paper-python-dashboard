#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Модуль для конвертации SVG в изображения для epd2in15g дисплея.
Поддерживает конвертацию из файлов и строк SVG.

УСТАНОВКА ЗАВИСИМОСТЕЙ:
----------------------
Вариант 1 (через apt, рекомендуется):
    sudo apt update
    sudo apt install python3-cairosvg

Вариант 2 (через pip для пользователя):
    pip install --user cairosvg

Вариант 3 (альтернатива через apt):
    sudo apt install python3-svglib python3-reportlab

Вариант 4 (альтернатива через pip для пользователя):
    pip install --user svglib reportlab

ПРИМЕЧАНИЕ: Для cairosvg также требуется системная библиотека:
    sudo apt install libcairo2-dev
"""

import os
import logging
from io import BytesIO, StringIO
from PIL import Image

SVG_EXAMPLES = {
    'sun': '''<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 50 50">
  <circle cx="25" cy="25" r="8" fill="#FFD700" stroke="#FFA500" stroke-width="1.5"/>
  <line x1="33" y1="25" x2="45" y2="25" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
  <line x1="31.93" y1="29" x2="42.32" y2="35" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
  <line x1="29" y1="31.93" x2="35" y2="42.32" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
  <line x1="25" y1="33" x2="25" y2="45" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
  <line x1="21" y1="31.93" x2="15" y2="42.32" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
  <line x1="18.07" y1="29" x2="7.68" y2="35" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
  <line x1="17" y1="25" x2="5" y2="25" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
  <line x1="18.07" y1="21" x2="7.68" y2="15" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
  <line x1="21" y1="18.07" x2="15" y2="7.68" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
  <line x1="25" y1="17" x2="25" y2="5" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
  <line x1="29" y1="18.07" x2="35" y2="7.68" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
  <line x1="31.93" y1="21" x2="42.32" y2="15" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
</svg>''',

    'cloud': '''<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 50 50">
  <path d="M 15 30 Q 10 30 10 35 Q 10 40 15 40 L 35 40 Q 40 40 40 35 Q 40 30 35 30 Q 35 25 30 25 Q 25 20 20 25 Q 15 25 15 30 Z" fill="#CCCCCC" stroke="#999999" stroke-width="4"/>
</svg>''',

    'rain': '''<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 50 50">
  <path d="M 15 30 Q 10 30 10 35 Q 10 40 15 40 L 35 40 Q 40 40 40 35 Q 40 30 35 30 Q 35 25 30 25 Q 25 20 20 25 Q 15 25 15 30 Z" fill="#CCCCCC" stroke="#999999" stroke-width="4"/>
  <line x1="20" y1="40" x2="18" y2="45" stroke="#4A90E2" stroke-width="3" stroke-linecap="round"/>
  <line x1="25" y1="40" x2="23" y2="45" stroke="#4A90E2" stroke-width="3" stroke-linecap="round"/>
  <line x1="30" y1="40" x2="28" y2="45" stroke="#4A90E2" stroke-width="3" stroke-linecap="round"/>
</svg>''',

    'snow': '''<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 50 50">
  <path d="M 15 30 Q 10 30 10 35 Q 10 40 15 40 L 35 40 Q 40 40 40 35 Q 40 30 35 30 Q 35 25 30 25 Q 25 20 20 25 Q 15 25 15 30 Z" fill="#E0E0E0" stroke="#999999" stroke-width="4"/>
  <circle cx="20" cy="42" r="4" fill="#CCCCCC"/>
  <circle cx="25" cy="45" r="4" fill="#CCCCCC"/>
  <circle cx="30" cy="42" r="4" fill="#CCCCCC"/>
</svg>''',

    'wind': '''<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 50 50">
  <path d="M 5 20 Q 15 20 20 15 Q 25 10 35 10" stroke="#888888" stroke-width="4" fill="none" stroke-linecap="round"/>
  <path d="M 5 30 Q 15 30 20 25 Q 25 20 35 20" stroke="#888888" stroke-width="4" fill="none" stroke-linecap="round"/>
  <path d="M 5 40 Q 15 40 20 35 Q 25 30 35 30" stroke="#888888" stroke-width="4" fill="none" stroke-linecap="round"/>
</svg>''',

    'thermometer': '''<svg xmlns="http://www.w3.org/2000/svg" width="30" height="50" viewBox="0 0 30 50">
  <rect x="10" y="5" width="10" height="35" rx="5" fill="#CC0000" stroke="#990000" stroke-width="2"/>
  <circle cx="15" cy="45" r="8" fill="#CC0000" stroke="#990000" stroke-width="2"/>
  <line x1="15" y1="10" x2="15" y2="35" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round"/>
</svg>''',

    'arrow_up': '''<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">
  <path d="M 15 5 L 25 20 L 20 20 L 20 25 L 10 25 L 10 20 L 5 20 Z" fill="#000000"/>
</svg>''',

    'arrow_down': '''<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">
  <path d="M 15 25 L 25 10 L 20 10 L 20 5 L 10 5 L 10 10 L 5 10 Z" fill="#000000"/>
</svg>''',

    'arrow_right': '''<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">
  <path d="M 5 15 L 20 5 L 20 10 L 25 10 L 25 20 L 20 20 L 20 25 Z" fill="#000000"/>
</svg>''',

    'arrow_left': '''<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">
  <path d="M 25 15 L 10 5 L 10 10 L 5 10 L 5 20 L 10 20 L 10 25 Z" fill="#000000"/>
</svg>''',

    'check': '''<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">
  <path d="M 5 15 L 12 22 L 25 8" stroke="#00AA00" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>''',

    'cross': '''<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">
  <line x1="5" y1="5" x2="25" y2="25" stroke="#CC0000" stroke-width="4" stroke-linecap="round"/>
  <line x1="25" y1="5" x2="5" y2="25" stroke="#CC0000" stroke-width="4" stroke-linecap="round"/>
</svg>''',

    'wifi': '''<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
  <path d="M 20 10 Q 5 10 5 25" stroke="#000000" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M 20 15 Q 10 15 10 25" stroke="#000000" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M 20 20 Q 15 20 15 25" stroke="#000000" stroke-width="3" fill="none" stroke-linecap="round"/>
  <circle cx="20" cy="25" r="2" fill="#000000"/>
</svg>''',

    'battery': '''<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20" viewBox="0 0 40 20">
  <rect x="2" y="5" width="30" height="10" rx="2" fill="none" stroke="#000000" stroke-width="2"/>
  <rect x="32" y="8" width="2" height="4" fill="#000000"/>
  <rect x="4" y="7" width="26" height="6" fill="#00AA00"/>
</svg>''',

    'home': '''<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
  <path d="M 20 5 L 5 20 L 8 20 L 8 35 L 15 35 L 15 25 L 25 25 L 25 35 L 32 35 L 32 20 L 35 20 Z" fill="#000000"/>
</svg>''',
}


def svg_to_epd_image(svg_path_or_string, epd, width=None, height=None, background_color='white'):
    """
    Конвертирует SVG файл или строку в изображение для epd2in15g дисплея.
    
    Args:
        svg_path_or_string: Путь к SVG файлу или SVG строка
        epd: Экземпляр epd2in15g.EPD()
        width: Ширина выходного изображения (по умолчанию epd.width)
        height: Высота выходного изображения (по умолчанию epd.height)
        background_color: Цвет фона ('white', 'black', 'transparent')
    
    Returns:
        PIL.Image: Изображение готовое для отображения на epd2in15g
    """
    try:
        import cairosvg
    except ImportError:
        logging.warning("cairosvg не найден, пробую альтернативный метод...")
        logging.info("Для установки: sudo apt install python3-cairosvg или pip install --user cairosvg")
        return svg_to_epd_image_alt(svg_path_or_string, epd, width, height, background_color)
    
    if width is None:
        width = epd.width
    if height is None:
        height = epd.height
    
    bg_color_map = {
        'white': (255, 255, 255),
        'black': (0, 0, 0),
        'transparent': None
    }
    bg_rgb = bg_color_map.get(background_color.lower(), (255, 255, 255))
    
    try:
        if os.path.exists(svg_path_or_string):
            svg_data = open(svg_path_or_string, 'rb').read()
        else:
            svg_data = svg_path_or_string.encode('utf-8') if isinstance(svg_path_or_string, str) else svg_path_or_string
        
        png_data = cairosvg.svg2png(
            bytestring=svg_data,
            output_width=width,
            output_height=height
        )
        
        image = Image.open(BytesIO(png_data))
        
        if bg_rgb and image.mode == 'RGBA':
            background = Image.new('RGB', image.size, bg_rgb)
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        return image
        
    except Exception as e:
        logging.error(f"Ошибка конвертации SVG (cairosvg): {e}")
        return svg_to_epd_image_alt(svg_path_or_string, epd, width, height, background_color)


def svg_to_epd_image_alt(svg_path_or_string, epd, width=None, height=None, background_color='white'):
    """
    Альтернативная функция конвертации SVG используя svglib.
    
    Args:
        svg_path_or_string: Путь к SVG файлу или SVG строка
        epd: Экземпляр epd2in15g.EPD()
        width: Ширина выходного изображения (по умолчанию epd.width)
        height: Высота выходного изображения (по умолчанию epd.height)
        background_color: Цвет фона ('white', 'black')
    
    Returns:
        PIL.Image: Изображение готовое для отображения на epd2in15g
    """
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
    except ImportError:
        logging.error("svglib не установлен.")
        logging.error("Для установки:")
        logging.error("  sudo apt install python3-svglib python3-reportlab")
        logging.error("  или: pip install --user svglib reportlab")
        logging.error("  или: sudo apt install python3-cairosvg")
        return None
    
    if width is None:
        width = epd.width
    if height is None:
        height = epd.height
    
    bg_color_map = {
        'white': (255, 255, 255),
        'black': (0, 0, 0)
    }
    bg_rgb = bg_color_map.get(background_color.lower(), (255, 255, 255))
    
    try:
        if os.path.exists(svg_path_or_string):
            drawing = svg2rlg(svg_path_or_string)
        else:
            drawing = svg2rlg(StringIO(svg_path_or_string))
        
        if drawing is None:
            logging.error("Не удалось загрузить SVG")
            return None
        
        drawing.width = width
        drawing.height = height
        
        img_data = renderPM.drawToString(drawing, fmt='PNG', dpi=72)
        image = Image.open(BytesIO(img_data))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        if background_color.lower() == 'white':
            background = Image.new('RGB', image.size, bg_rgb)
            if image.mode == 'RGBA':
                background.paste(image, mask=image.split()[3])
            else:
                background.paste(image)
            image = background
        
        return image
        
    except Exception as e:
        logging.error(f"Ошибка конвертации SVG (svglib): {e}")
        return None


def get_example_svg(name):
    """
    Получить встроенный пример SVG по имени.
    
    Args:
        name: Имя примера ('sun', 'cloud', 'rain', 'snow', 'wind', 
              'thermometer', 'arrow_up', 'arrow_down', 'arrow_right', 
              'arrow_left', 'check', 'cross', 'wifi', 'battery', 'home')
    
    Returns:
        str: SVG строка или None если пример не найден
    """
    return SVG_EXAMPLES.get(name.lower())


def list_examples():
    """
    Получить список доступных примеров SVG.
    
    Returns:
        list: Список имен доступных примеров
    """
    return list(SVG_EXAMPLES.keys())


def example_to_image(name, epd, width=None, height=None, background_color='white'):
    """
    Конвертировать встроенный пример SVG в изображение.
    
    Args:
        name: Имя примера из SVG_EXAMPLES
        epd: Экземпляр epd2in15g.EPD()
        width: Ширина выходного изображения
        height: Высота выходного изображения
        background_color: Цвет фона
    
    Returns:
        PIL.Image: Изображение или None если пример не найден
    """
    svg_string = get_example_svg(name)
    if svg_string is None:
        logging.warning(f"Пример '{name}' не найден. Доступные: {list_examples()}")
        return None
    
    return svg_to_epd_image(svg_string, epd, width, height, background_color)


if __name__ == '__main__':
    print("Доступные примеры SVG:")
    for name in list_examples():
        print(f"  - {name}")
    
    print("\nПример использования:")
    print("""
from lib.svg_converter import example_to_image, svg_to_epd_image
from waveshare_epd import epd2in15g

epd = epd2in15g.EPD()

# Использование встроенного примера
sun_icon = example_to_image('sun', epd, width=50, height=50)

# Использование собственного SVG
custom_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50">...</svg>'
custom_icon = svg_to_epd_image(custom_svg, epd, width=50, height=50)

# Использование SVG файла
file_icon = svg_to_epd_image('path/to/icon.svg', epd, width=50, height=50)
""")

