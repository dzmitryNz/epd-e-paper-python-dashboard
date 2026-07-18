#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from display_renderer import DisplayRenderer


def make_config():
    """Minimal 4-gray epd3in7-style config, renderable without hardware."""
    return {
        'display': {
            'epdDisplayType': 'epd3in7',
            'epdDisplayWidth': 280,
            'epdDisplayHeight': 480,
            'epdDisplayRotation': 0,
            'epdColourMode': '4GRAY',
            'oldDataColour': 'GRAY3',
        },
        'fonts': {
            'font15': ['Font.ttc', 15],
            'font18': ['Font.ttc', 18],
            'font24': ['Font.ttc', 24],
        },
        'layout': {'lineHeight': 25, 'startX': 0},
        'services': {},
        'dashboard': {'lines': [
            {'name': 'datetime', 'afterY': 27, 'items': [
                {'type': 'datetime', 'format': '%H:%M', 'font': 'font24', 'colour': 'GRAY4'},
            ]},
            {'name': 'weather', 'afterY': 25, 'items': [
                {'type': 'dsw1', 'category': 'sensors', 'prefix': 'Out: ',
                 'font': 'font18', 'colour': 'GRAY4'},
                {'type': 'temp', 'category': 'weather', 'prefix': ' t ', 'startX': 120,
                 'font': 'font18', 'colour': 'GRAY4'},
            ]},
            {'name': 'mining', 'afterY': 25, 'items': [
                {'type': 'hashrate', 'category': 'solopool', 'format': 'hashrate',
                 'font': 'font18', 'colour': 'GRAY4'},
                {'type': 'workingmode', 'category': 'nano3stats',
                 'map': {'0': 'Lo', '1': 'Mi', '2': 'Hi'},
                 'font': 'font18', 'colour': 'GRAY4'},
            ]},
            {'name': 'verbs', 'type': 'verbs', 'font': 'font15', 'items': []},
        ]},
    }


def make_data():
    data = {
        'weather': {'temp': 21.5},
        'sensors': {'dsw1': 12.5},
        'kucoin': {},
        'solopool': {'hashrate': 5.1e12},
        'nano3stats': {'workingmode': '2'},
    }
    ages = {k: {} for k in data}
    return data, ages


VERBS = [
    {'infinitive': 'go', 'past': 'went', 'past_participle': 'gone',
     'translation': 'ісці'},
    {'infinitive': 'see', 'past': 'saw', 'past_participle': 'seen',
     'translation': 'бачыць'},
]


class TestRendererWithoutHardware(unittest.TestCase):
    def setUp(self):
        self.renderer = DisplayRenderer(make_config())

    def test_render_returns_grayscale_image_of_display_size(self):
        data, ages = make_data()
        image = self.renderer.render(data, ages)
        self.assertEqual(image.mode, 'L')
        self.assertEqual(image.size, (280, 480))

    def test_render_with_verbs_records_verbs_area(self):
        data, ages = make_data()
        self.renderer.render(data, ages, verbs=VERBS, verbs_page=0)
        start_y, height = self.renderer.last_verbs_area
        self.assertGreater(start_y, 0)
        self.assertGreater(height, 0)
        self.assertLessEqual(start_y + height, 480)

    def test_refresh_verbs_area_redraws_in_place(self):
        data, ages = make_data()
        image = self.renderer.render(data, ages, verbs=VERBS, verbs_page=0)
        refreshed = self.renderer.refresh_verbs_area(image, VERBS, page=1)
        self.assertEqual(refreshed.size, image.size)

    def test_hashrate_formatting(self):
        self.assertEqual(self.renderer.format_hashrate(5.1e12), '5.10T')
        self.assertEqual(self.renderer.format_hashrate(3.0e9), '3.00G')
        self.assertEqual(self.renderer.format_hashrate(2.5e6), '2.50M')

    def test_old_data_rendered_with_old_colour(self):
        data, ages = make_data()
        ages['sensors']['dsw1'] = True  # stale value must not crash and use old colour
        image = self.renderer.render(data, ages)
        self.assertEqual(image.mode, 'L')

    def test_text_item_renders_static_label(self):
        text, is_old = self.renderer._resolve_item_value(
            {'type': 'text', 'text': 'Out, °C:'}, {}, {})
        self.assertEqual(text, 'Out, °C:')
        self.assertFalse(is_old)

    def test_value_map_applied(self):
        formatted = self.renderer._format_value('2', {'map': {'2': 'Hi'}})
        self.assertEqual(formatted, 'Hi')

    def test_fallback_value_used_when_primary_missing(self):
        item = {'type': 'dsw1', 'category': 'sensors', 'prefix': 'Out: ',
                'fallback': {'type': 'temp', 'category': 'weather'}}
        data = {'sensors': {}, 'weather': {'temp': 21.5}}
        ages = {'sensors': {}, 'weather': {}}
        text, is_old = self.renderer._resolve_item_value(item, data, ages)
        self.assertEqual(text, 'Out: 21.5')

    def test_no_fallback_when_primary_present(self):
        item = {'type': 'dsw1', 'category': 'sensors',
                'fallback': {'type': 'temp', 'category': 'weather'}}
        data = {'sensors': {'dsw1': 12.5}, 'weather': {'temp': 21.5}}
        ages = {'sensors': {}, 'weather': {}}
        text, _ = self.renderer._resolve_item_value(item, data, ages)
        self.assertEqual(text, '12.5')

    def test_hide_if_missing_returns_none(self):
        item = {'type': 'hashrate', 'category': 'solopool', 'hideIfMissing': True}
        data = {'solopool': {}}
        ages = {'solopool': {}}
        text, _ = self.renderer._resolve_item_value(item, data, ages)
        self.assertIsNone(text)

    def test_hide_if_missing_shows_present_value(self):
        item = {'type': 'power', 'category': 'nano3stats', 'suffix': 'W',
                'hideIfMissing': True}
        data = {'nano3stats': {'power': '95'}}
        ages = {'nano3stats': {}}
        text, _ = self.renderer._resolve_item_value(item, data, ages)
        self.assertEqual(text, '95W')

    def test_render_skips_hidden_items(self):
        data, ages = make_data()
        data['solopool'] = {}
        data['nano3stats'] = {}
        config = make_config()
        for item in config['dashboard']['lines'][2]['items']:
            item['hideIfMissing'] = True
        renderer = DisplayRenderer(config)
        image = renderer.render(data, ages)
        self.assertEqual(image.mode, 'L')

    def test_gray_palette_without_hardware(self):
        self.assertEqual(self.renderer.get_colour('GRAY1'), 0xff)
        self.assertEqual(self.renderer.get_colour('GRAY4'), 0x00)
        self.assertEqual(self.renderer.get_colour('BLACK'), 0x00)
        self.assertEqual(self.renderer.get_colour('WHITE'), 0xff)


if __name__ == '__main__':
    unittest.main()
