#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import sys
import json
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verbs import (load_verbs, load_verbs_state, save_verbs_state,
                   calculate_verbs_per_page, advance_verbs_page)


class TestVerbsPagination(unittest.TestCase):
    def test_verbs_per_page(self):
        self.assertEqual(calculate_verbs_per_page(25, 250), 10)
        self.assertEqual(calculate_verbs_per_page(25, 10), 1)   # minimum 1
        self.assertEqual(calculate_verbs_per_page(25, 0), 0)

    def test_advance_wraps_around(self):
        # 5 verbs, 2 per page -> 3 pages
        self.assertEqual(advance_verbs_page(0, total_verbs=5, verbs_per_page=2), 1)
        self.assertEqual(advance_verbs_page(2, total_verbs=5, verbs_per_page=2), 0)

    def test_advance_with_no_verbs(self):
        self.assertEqual(advance_verbs_page(3, total_verbs=0, verbs_per_page=2), 0)


class TestVerbsState(unittest.TestCase):
    def test_state_round_trip(self):
        path = os.path.join(tempfile.mkdtemp(), 'state.json')
        state = {'current_page': 4, 'last_update_time': 123.5}
        save_verbs_state(state, path)
        self.assertEqual(load_verbs_state(path), state)

    def test_missing_state_gives_defaults(self):
        state = load_verbs_state('/nonexistent/state.json')
        self.assertEqual(state, {'current_page': 0, 'last_update_time': 0})


class TestLoadVerbs(unittest.TestCase):
    def test_loads_existing_file(self):
        path = os.path.join(tempfile.mkdtemp(), 'verbs.json')
        verbs = [{'infinitive': 'go', 'past': 'went', 'past_participle': 'gone'}]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(verbs, f)
        self.assertEqual(load_verbs(path), verbs)

    def test_missing_file_creates_defaults(self):
        path = os.path.join(tempfile.mkdtemp(), 'verbs.json')
        verbs = load_verbs(path)
        self.assertTrue(len(verbs) > 0)
        self.assertIn('infinitive', verbs[0])
        self.assertTrue(os.path.exists(path))


if __name__ == '__main__':
    unittest.main()
