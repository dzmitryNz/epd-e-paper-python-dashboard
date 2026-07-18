#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import sys
import time
import logging
import importlib
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Optional, Tuple, List

iconsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'icons')
fontsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fonts')
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

# Fallback palettes used when the EPD driver is not loaded (tests, --dry-run)
GRAY_PALETTE = {
    'WHITE': 0xff, 'GRAY1': 0xff, 'GRAY2': 0xC0,
    'GRAY3': 0x80, 'GRAY4': 0x00, 'BLACK': 0x00,
}
RGB_PALETTE = {
    'WHITE': 0xffffff, 'BLACK': 0x000000,
    'RED': 0x0000ff, 'YELLOW': 0x00ffff,
}


class DisplayRenderer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        display = config['display']
        self.epd_type = display['epdDisplayType']
        self.colour_mode = display.get('epdColourMode', 'RGB')
        self.old_data_colour = display.get('oldDataColour', 'GRAY3')
        # display params may come from .env as strings
        self.rotation = int(display.get('epdDisplayRotation', 0) or 0)
        self.epd = None  # hardware driver, loaded in init_display()

        self.fonts = self._load_fonts()
        self.line_height = config['layout'].get('lineHeight', 25)
        self.start_x = config['layout'].get('startX', 0)

        width = int(display.get('epdDisplayWidth', 280) or 280)
        height = int(display.get('epdDisplayHeight', 480) or 480)
        if self.rotation in [90, 270]:
            self.image_width, self.image_height = height, width
        else:
            self.image_width, self.image_height = width, height

        self.image_mode = 'L' if self.colour_mode == '4GRAY' else 'RGB'
        self.last_verbs_area: Optional[Tuple[int, int]] = None

    def _load_fonts(self) -> Dict[str, ImageFont.FreeTypeFont]:
        """Loads fonts from configuration"""
        fonts = {}
        for font_name, font_config in self.config.get('fonts', {}).items():
            font_file, font_size = font_config
            font_path = os.path.join(fontsdir, font_file)
            try:
                fonts[font_name] = ImageFont.truetype(font_path, font_size)
            except Exception as e:
                logging.warning(f"Failed to load font {font_name}: {e}")
                fonts[font_name] = ImageFont.load_default()
        return fonts

    def get_colour(self, colour_name: str, is_old_data: bool = False) -> Any:
        """Maps a colour name to a pixel value, preferring driver constants"""
        if is_old_data:
            colour_name = self.old_data_colour

        if self.epd is not None and hasattr(self.epd, colour_name):
            return getattr(self.epd, colour_name)

        palette = GRAY_PALETTE if self.image_mode == 'L' else RGB_PALETTE
        return palette.get(colour_name, palette['BLACK'])

    def format_hashrate(self, value: Any) -> str:
        """Formats a raw H/s value as T/G/M shorthand"""
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 'N/A'
        if value >= 1e12:
            return f"{value / 1e12:.2f}T"
        if value >= 1e9:
            return f"{value / 1e9:.2f}G"
        return f"{value / 1e6:.2f}M"

    def _format_datetime(self, fmt: str) -> str:
        return time.strftime(fmt, time.localtime())

    def _format_sun_time(self, timestamp: int, fmt: str) -> str:
        return time.strftime(fmt, time.localtime(timestamp))

    def _get_wind_direction(self, wind_deg: int) -> str:
        directions = ['С', 'СВ', 'В', 'ЮВ', 'Ю', 'ЮЗ', 'З', 'СЗ']
        return directions[int((wind_deg / 45) + 0.5) % 8]

    def _guess_category(self, item_type: str) -> str:
        """Backward-compatible category detection for items without 'category'"""
        if item_type in ['temp', 'feels_like', 'humidity', 'pressure', 'wind_speed',
                         'wind_direction', 'clouds', 'description', 'sunrise', 'sunset',
                         'weather_icon']:
            return 'weather'
        if '-' in item_type:
            return 'kucoin'
        return 'sensors'

    def _get_value(self, data: Dict[str, Any], data_ages: Dict[str, Dict[str, bool]],
                   item_type: str, category: str) -> Tuple[Any, bool]:
        """Gets value from data and flag indicating if it's old"""
        category_data = data.get(category, {})

        if category == 'weather' and item_type == 'wind_direction':
            if 'wind_deg' in category_data and category_data['wind_deg'] is not None:
                value = self._get_wind_direction(category_data['wind_deg'])
            else:
                value = None
            is_old = data_ages.get(category, {}).get('wind_deg', False)
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
        prefix = item_config.get('prefix', '')
        suffix = item_config.get('suffix', '')

        if value is None or value == 'N/A':
            return f"{prefix}N/A"

        value_map = item_config.get('map')
        if value_map:
            value = value_map.get(str(value), value)

        if item_config.get('format') == 'hashrate':
            value = self.format_hashrate(value)
        elif isinstance(value, float) and value == int(value):
            value = str(int(value))

        return f"{prefix}{value}{suffix}"

    def _text_width(self, font: ImageFont.FreeTypeFont, text: str) -> int:
        try:
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0]
        except AttributeError:
            return font.getsize(text)[0]

    def _resolve_item_value(self, item_config: Dict[str, Any], data: Dict[str, Any],
                            data_ages: Dict[str, Dict[str, bool]]) -> Tuple[str, bool]:
        """Resolves a dashboard item to its display text and staleness flag"""
        item_type = item_config.get('type', '')

        if item_type == 'text':
            return item_config.get('text', ''), False

        if item_type == 'datetime':
            fmt = item_config.get('format', '%a - %d %b - %H:%M')
            return self._format_datetime(fmt), False

        category = item_config.get('category') or self._guess_category(item_type)
        value, is_old = self._get_value(data, data_ages, item_type, category)

        if item_type in ('sunrise', 'sunset') and value != 'N/A':
            value = self._format_sun_time(value, item_config.get('format', '%H:%M'))
        elif category == 'kucoin' and value != 'N/A' and isinstance(value, (int, float)):
            value = f"${value}"

        return self._format_value(value, item_config), is_old

    def render(self, data: Dict[str, Any], data_ages: Dict[str, Dict[str, bool]],
               verbs: Optional[List[Dict[str, Any]]] = None, verbs_page: int = 0) -> Image.Image:
        """Renders all data on image"""
        background = self.get_colour('WHITE')
        image = Image.new(self.image_mode, (self.image_width, self.image_height), background)
        draw = ImageDraw.Draw(image)

        y_pos = 0
        self.last_verbs_area = None

        for line_config in self.config['dashboard'].get('lines', []):
            if line_config.get('type') == 'verbs':
                start_y = line_config.get('startY', y_pos)
                area_height = self.image_height - start_y
                self.last_verbs_area = (start_y, area_height)
                if verbs:
                    self._draw_verbs(draw, line_config, verbs, verbs_page, start_y, area_height)
                break  # verbs section fills the rest of the screen

            line_start_y = line_config.get('startY', y_pos)
            if line_start_y >= 0:
                y_pos = line_start_y

            line_start_x = line_config.get('startX', self.start_x)
            x_pos = line_start_x

            for item_config in line_config.get('items', []):
                item_x = item_config.get('startX', item_config.get('startY', 0))
                if item_x > 0:
                    x_pos = line_start_x + item_x

                font = self.fonts.get(item_config.get('font', 'font18'),
                                      next(iter(self.fonts.values())))
                display_text, is_old = self._resolve_item_value(item_config, data, data_ages)
                colour = self.get_colour(item_config.get('colour', 'BLACK'), is_old)

                item_y = y_pos + item_config.get('offsetY', 0)
                draw.text((x_pos, item_y), display_text, font=font, fill=colour)
                x_pos += self._text_width(font, display_text) + item_config.get('afterX', 0)

            y_pos += line_config.get('afterY', self.line_height)

            if y_pos > self.image_height - 20:
                break

        if self.rotation != 0:
            image = image.rotate(-self.rotation, expand=True, fillcolor=background)

        return image

    def _draw_verbs(self, draw: ImageDraw.ImageDraw, line_config: Dict[str, Any],
                    verbs: List[Dict[str, Any]], page: int, y_pos: int, max_height: int):
        """Draws paginated verbs table with translations, descriptions and examples"""
        font = self.fonts.get(line_config.get('font', 'font15'),
                              next(iter(self.fonts.values())))
        color = self.get_colour(line_config.get('colour', 'BLACK'))
        unit_color = self.get_colour(line_config.get('secondaryColour',
                                                     line_config.get('colour', 'BLACK')))
        line_height = line_config.get('lineHeight', self.line_height)

        draw.line([(self.start_x, y_pos), (self.image_width, y_pos)], fill=color, width=1)
        y_pos += 3

        verbs_per_page = max(1, (max_height - 3) // line_height)
        total_pages = (len(verbs) + verbs_per_page - 1) // verbs_per_page
        if total_pages == 0:
            return
        if page >= total_pages:
            page = 0

        page_verbs = verbs[page * verbs_per_page:(page + 1) * verbs_per_page]

        max_inf = max(len(v['infinitive']) for v in page_verbs)
        max_past = max(len(v['past']) for v in page_verbs)
        max_part = max(len(v['past_participle']) for v in page_verbs)

        if page_verbs and page_verbs[0].get('translations'):
            trans = page_verbs[0]['translations']
            max_inf = max(max_inf, len(trans.get('infinitive', '')))
            max_past = max(max_past, len(trans.get('past', '')))
            max_part = max(max_part, len(trans.get('past_participle', '')))

        current_y = y_pos
        max_y = y_pos + max_height + 5

        for idx, verb in enumerate(page_verbs):
            if current_y + line_height > max_y:
                break

            if idx == 0 and verb.get('translations'):
                trans = verb['translations']
                trans_text = (f"{trans.get('infinitive', ''):<{max_inf}} | "
                              f"{trans.get('past', ''):<{max_past}} | "
                              f"{trans.get('past_participle', ''):<{max_part}}")
                draw.text((self.start_x, current_y), trans_text, font=font, fill=unit_color)
                current_y += line_height - 3

            verb_text = (f"{verb['infinitive']:<{max_inf}} | "
                         f"{verb['past']:<{max_past}} | "
                         f"{verb['past_participle']:<{max_part}}")
            draw.text((self.start_x, current_y), verb_text, font=font, fill=color)
            current_y += line_height - 3

            if verb.get('description'):
                if current_y + line_height - 5 > max_y:
                    break
                draw.text((self.start_x + 5, current_y), f"  {verb['description']}",
                          font=font, fill=unit_color)
                current_y += line_height - 5

            if verb.get('examples'):
                if current_y + line_height - 5 > max_y:
                    break
                example = verb['examples'][0]
                translation = verb.get('translation', '')
                max_total_len = 45
                if translation:
                    translation_len = min(len(translation), 18)
                    example_len = max_total_len - translation_len - 8
                    if len(example) > example_len:
                        example = example[:example_len - 3] + "..."
                    if len(translation) > translation_len:
                        translation = translation[:translation_len - 3] + "..."
                    example_text = f"{translation} ex: {example}"
                else:
                    if len(example) > max_total_len - 6:
                        example = example[:max_total_len - 9] + "..."
                    example_text = f"ex: {example}"
                draw.text((self.start_x + 5, current_y), example_text, font=font, fill=unit_color)
                current_y += line_height - 5

            current_y += 2

    def refresh_verbs_area(self, image: Image.Image, verbs: List[Dict[str, Any]],
                           page: int) -> Image.Image:
        """Redraws only the verbs area on an existing image"""
        if not self.last_verbs_area:
            return image

        start_y, area_height = self.last_verbs_area
        draw = ImageDraw.Draw(image)
        draw.rectangle([(0, start_y), (self.image_width, start_y + area_height)],
                       fill=self.get_colour('WHITE'))

        verbs_line = next((line for line in self.config['dashboard'].get('lines', [])
                           if line.get('type') == 'verbs'), {})
        self._draw_verbs(draw, verbs_line, verbs, page, start_y, area_height)
        return image

    def verbs_per_page(self) -> int:
        """How many verbs fit into the last rendered verbs area"""
        if not self.last_verbs_area:
            return 0
        _, area_height = self.last_verbs_area
        return max(1, (area_height - 3) // self.line_height)

    def init_display(self):
        """Loads the EPD driver and initializes hardware"""
        logging.info(f"Initializing display {self.epd_type}")
        driver = importlib.import_module(f'waveshare_epd.{self.epd_type}')
        self.epd = driver.EPD()
        if self.colour_mode == '4GRAY':
            self.epd.init(0)
        else:
            self.epd.init()

    def display_image(self, image: Image.Image):
        """Displays image on the hardware"""
        if self.epd is None:
            logging.info("No hardware initialized, skipping display update")
            return
        if self.colour_mode == '4GRAY':
            self.epd.display_4Gray(self.epd.getbuffer_4Gray(image))
        else:
            try:
                self.epd.display(self.epd.getbuffer(image))
            except AttributeError:
                self.epd.Display(self.epd.getbuffer(image))

    def sleep(self):
        """Puts display into sleep mode"""
        if self.epd is None:
            return
        logging.info("Going to sleep...")
        self.epd.sleep()
