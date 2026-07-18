#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import sys
import json
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import load_env_file, resolve_env, load_config


class TestLoadEnvFile(unittest.TestCase):
    def _write_env(self, content):
        f = tempfile.NamedTemporaryFile('w', suffix='.env', delete=False)
        f.write(content)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_loads_plain_and_quoted_values(self):
        path = self._write_env(
            "# comment\n"
            "PLAIN=value1\n"
            "DQUOTED=\"value 2\"\n"
            "SQUOTED='value 3'\n"
            "\n"
        )
        for key in ('PLAIN', 'DQUOTED', 'SQUOTED'):
            os.environ.pop(key, None)
            self.addCleanup(os.environ.pop, key, None)
        self.assertTrue(load_env_file(path))
        self.assertEqual(os.environ['PLAIN'], 'value1')
        self.assertEqual(os.environ['DQUOTED'], 'value 2')
        self.assertEqual(os.environ['SQUOTED'], 'value 3')

    def test_missing_file_returns_false(self):
        self.assertFalse(load_env_file('/nonexistent/.env'))


class TestResolveEnv(unittest.TestCase):
    def setUp(self):
        os.environ['TEST_URL'] = 'http://10.0.0.1/sensors'
        os.environ['TEST_KEY'] = 'secret'
        self.addCleanup(os.environ.pop, 'TEST_URL', None)
        self.addCleanup(os.environ.pop, 'TEST_KEY', None)

    def test_resolves_env_prefix_string(self):
        self.assertEqual(resolve_env('env.TEST_URL'), 'http://10.0.0.1/sensors')

    def test_resolves_dollar_brace_string(self):
        self.assertEqual(resolve_env('${TEST_KEY}'), 'secret')

    def test_plain_string_untouched(self):
        self.assertEqual(resolve_env('hello'), 'hello')

    def test_missing_var_returns_empty_string(self):
        os.environ.pop('NO_SUCH_VAR_12345', None)
        self.assertEqual(resolve_env('env.NO_SUCH_VAR_12345'), '')

    def test_resolves_recursively_in_dicts_and_lists(self):
        tree = {
            'services': {
                'a': {'url': 'env.TEST_URL', 'params': ['${TEST_KEY}', 42]},
            },
            'number': 7,
        }
        resolved = resolve_env(tree)
        self.assertEqual(resolved['services']['a']['url'], 'http://10.0.0.1/sensors')
        self.assertEqual(resolved['services']['a']['params'], ['secret', 42])
        self.assertEqual(resolved['number'], 7)


class TestLoadConfigResolvesEnv(unittest.TestCase):
    def test_load_config_substitutes_env_values(self):
        os.environ['CFG_TEST_URL'] = 'http://192.168.9.9/sensors'
        self.addCleanup(os.environ.pop, 'CFG_TEST_URL', None)
        cfg = {'services': {'s': {'url': 'env.CFG_TEST_URL'}}}
        f = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
        json.dump(cfg, f)
        f.close()
        self.addCleanup(os.unlink, f.name)

        loaded = load_config(f.name)
        self.assertEqual(loaded['services']['s']['url'], 'http://192.168.9.9/sensors')


if __name__ == '__main__':
    unittest.main()
