#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_loader
from data_loader import merge_data_with_cache, load_all_data


class TestMergeWithCache(unittest.TestCase):
    def test_invalid_value_replaced_from_cache_and_flagged_old(self):
        current = {'dsw1': 'ERR', 'dsw2': '7.25'}
        cached = {'sensors': {'dsw1': '12.5'}}
        result, ages = merge_data_with_cache(current, cached, 'sensors')
        self.assertEqual(result['dsw1'], '12.5')
        self.assertTrue(ages['dsw1'])
        self.assertEqual(result['dsw2'], '7.25')
        self.assertFalse(ages['dsw2'])


class TestLoadAllData(unittest.TestCase):
    def test_includes_mining_categories(self):
        patches = {
            'fetch_weather_data': {'temp': 20.0},
            'fetch_kucoin_data': {'BTC-USDC': {'last': 50000}},
            'fetch_all_sensor_data': {'dsw1': 12.5},
            'fetch_solopool_data': {'hashrate': 1e12, 'luck': 90, 'blocks': 1},
            'fetch_nano3stats_data': {'workingmode': '1', 'power': '100'},
        }
        with mock.patch.multiple(
            data_loader,
            **{name: mock.Mock(return_value=value) for name, value in patches.items()}
        ):
            all_data, ages = load_all_data({'services': {}}, use_cache=False)

        self.assertEqual(all_data['solopool']['hashrate'], 1e12)
        self.assertEqual(all_data['nano3stats']['workingmode'], '1')
        self.assertEqual(all_data['weather']['temp'], 20.0)
        self.assertIn('solopool', ages)
        self.assertIn('nano3stats', ages)


if __name__ == '__main__':
    unittest.main()
