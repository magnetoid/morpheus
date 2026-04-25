"""Tests for the plugin engine: base class validation + scaffolder."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from plugins.base import MorpheusPlugin, PluginConfigurationError


class PluginMetadataValidationTests(SimpleTestCase):

    def test_valid_plugin_subclass(self):
        class Good(MorpheusPlugin):
            name = 'good_plug'
            label = 'Good Plug'
            version = '1.2.3'
        self.assertEqual(Good.name, 'good_plug')

    def test_invalid_name_camel_case(self):
        with self.assertRaises(PluginConfigurationError):
            class Bad(MorpheusPlugin):
                name = 'BadName'
                label = 'Bad'
                version = '1.0.0'

    def test_missing_label(self):
        with self.assertRaises(PluginConfigurationError):
            class NoLabel(MorpheusPlugin):
                name = 'no_label_plug'
                label = ''
                version = '1.0.0'

    def test_invalid_version(self):
        with self.assertRaises(PluginConfigurationError):
            class BadVer(MorpheusPlugin):
                name = 'bad_ver_plug'
                label = 'Bad Ver'
                version = 'oops'

    def test_requires_must_be_list_of_strings(self):
        with self.assertRaises(PluginConfigurationError):
            class BadReq(MorpheusPlugin):
                name = 'bad_req_plug'
                label = 'Bad Requires'
                version = '1.0.0'
                requires = ['ok', 123]  # type: ignore

    def test_register_hook_validates_handler(self):
        class P(MorpheusPlugin):
            name = 'register_validator'
            label = 'Register Validator'
            version = '0.1.0'
        with self.assertRaises(TypeError):
            P().register_hook('order.placed', 'not callable')

    def test_register_urls_outside_ready_raises(self):
        class P(MorpheusPlugin):
            name = 'urls_validator'
            label = 'URLs Validator'
            version = '0.1.0'
        with self.assertRaises(RuntimeError):
            P().register_urls('something.urls')


class MorphCreatePluginTests(SimpleTestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='morph-scaffold-'))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _scaffold(self, name: str, **flags) -> Path:
        call_command(
            'morph_create_plugin',
            name,
            target=str(self.tmp),
            **flags,
        )
        return self.tmp / name

    def test_scaffold_minimal(self):
        out = self._scaffold('hello_scaffold')
        self.assertTrue((out / '__init__.py').exists())
        self.assertTrue((out / 'apps.py').exists())
        self.assertTrue((out / 'plugin.py').exists())
        self.assertTrue((out / 'tests/test_smoke.py').exists())
        self.assertFalse((out / 'models.py').exists())
        self.assertFalse((out / 'urls.py').exists())

    def test_scaffold_with_models(self):
        out = self._scaffold('with_models_scaffold', with_models=True)
        self.assertTrue((out / 'models.py').exists())
        self.assertTrue((out / 'migrations/__init__.py').exists())

    def test_scaffold_with_graphql_urls_tasks(self):
        out = self._scaffold(
            'full_kit_scaffold',
            with_graphql=True,
            with_urls=True,
            with_tasks=True,
        )
        self.assertTrue((out / 'graphql/queries.py').exists())
        self.assertTrue((out / 'urls.py').exists())
        self.assertTrue((out / 'views.py').exists())
        self.assertTrue((out / 'tasks.py').exists())

    def test_scaffold_rejects_bad_name(self):
        with self.assertRaises(CommandError):
            call_command(
                'morph_create_plugin',
                'BadName',
                target=str(self.tmp),
            )

    def test_plugin_py_compiles(self):
        out = self._scaffold(
            'compile_scaffold', with_models=True, with_graphql=True,
        )
        plugin_py = (out / 'plugin.py').read_text()
        compile(plugin_py, str(out / 'plugin.py'), 'exec')
        graphql_py = (out / 'graphql/queries.py').read_text()
        compile(graphql_py, str(out / 'graphql/queries.py'), 'exec')
