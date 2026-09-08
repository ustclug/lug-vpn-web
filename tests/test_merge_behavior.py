import datetime
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

UTILS_PATH = Path(__file__).resolve().parents[1] / 'app' / 'utils.py'
UTILS_SPEC = importlib.util.spec_from_file_location('merge_utils', UTILS_PATH)
utils = importlib.util.module_from_spec(UTILS_SPEC)
UTILS_SPEC.loader.exec_module(utils)
LibraryAPIError = utils.LibraryAPIError
expiration_date = utils.expiration_date
fetch_from_lib_api = utils.fetch_from_lib_api


class ExpirationDateTests(unittest.TestCase):
    def test_semester_boundaries(self):
        cases = {
            datetime.date(2026, 2, 28): datetime.date(2026, 9, 1),
            datetime.date(2026, 3, 1): datetime.date(2027, 3, 1),
            datetime.date(2026, 8, 31): datetime.date(2027, 3, 1),
            datetime.date(2026, 9, 1): datetime.date(2027, 9, 1),
        }
        for today, expected in cases.items():
            with self.subTest(today=today):
                self.assertEqual(expiration_date('semester', today), expected)

    def test_year_boundaries(self):
        self.assertEqual(
            expiration_date('year', datetime.date(2026, 2, 28)),
            datetime.date(2026, 9, 20),
        )
        self.assertEqual(
            expiration_date('year', datetime.date(2026, 3, 1)),
            datetime.date(2027, 9, 20),
        )

    def test_long_is_semester_plus_three_calendar_years(self):
        today = datetime.date(2026, 9, 1)
        semester = expiration_date('semester', today)
        self.assertEqual(
            expiration_date('long', today),
            semester.replace(year=semester.year + 3),
        )

    def test_unknown_expiration_type_is_rejected(self):
        with self.assertRaises(ValueError):
            expiration_date('forever', datetime.date(2026, 1, 1))


class LibraryAPITests(unittest.TestCase):
    @patch.object(utils.requests, 'get')
    def test_request_contract_and_xml_parsing(self, get):
        response = Mock()
        response.content = b'<reader_info><status>ok</status><name>Alice</name></reader_info>'
        response.raise_for_status.return_value = None
        get.return_value = response

        result = fetch_from_lib_api('https://library.example/check', 'PB123', timeout=5)

        get.assert_called_once_with(
            'https://library.example/check', params={'id': 'PB123'}, timeout=5,
        )
        self.assertEqual(result, {'status': 'ok', 'name': 'Alice'})

    @patch.object(utils.requests, 'get')
    def test_xml_declaration_controls_chinese_text_decoding(self, get):
        response = Mock()
        response.content = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<reader_info><status>ok</status><name>张三</name>'
            '<type>教师</type></reader_info>'
        ).encode('utf-8')
        # This is how requests can misdecode application/xml without a charset.
        response.text = response.content.decode('iso-8859-1')
        response.raise_for_status.return_value = None
        get.return_value = response

        result = fetch_from_lib_api('https://library.example/check', '10483')

        self.assertEqual(result['name'], '张三')
        self.assertEqual(result['type'], '教师')

    @patch.object(utils.requests, 'get', side_effect=requests.Timeout)
    def test_network_errors_are_normalized(self, _get):
        with self.assertRaises(LibraryAPIError):
            fetch_from_lib_api('https://library.example/check', 'PB123')

    @patch.object(utils.requests, 'get')
    def test_malformed_xml_is_normalized(self, get):
        response = Mock()
        response.content = b'<not-closed>'
        response.raise_for_status.return_value = None
        get.return_value = response
        with self.assertRaises(LibraryAPIError):
            fetch_from_lib_api('https://library.example/check', 'PB123')


class RejectionTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from app.models import User, VPNAccount
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest('application dependencies are unavailable') from exc
        cls.User = User
        cls.VPNAccount = VPNAccount

    def make_user(self, status='pass', renewing=True):
        return SimpleNamespace(
            status=status,
            renewing=renewing,
            rejectreason=None,
            set_expiration=Mock(),
            save=Mock(),
        )

    def test_non_force_renewal_rejection_retains_active_status(self):
        user = self.make_user()
        expiration = datetime.date(2026, 12, 31)

        self.User.reject(user, 'not eligible', expiration, force=False)

        self.assertEqual(user.status, 'pass')
        self.assertFalse(user.renewing)
        user.set_expiration.assert_called_once_with(expiration, delete=False)
        user.save.assert_called_once_with()

    def test_force_rejection_terminates_service_and_marks_rejected(self):
        user = self.make_user()
        expiration = datetime.date(2026, 12, 31)

        self.User.reject(user, 'policy violation', expiration, force=True)

        self.assertEqual(user.status, 'reject')
        self.assertFalse(user.renewing)
        user.set_expiration.assert_called_once_with(expiration, delete=True)

    def test_force_expiration_deletes_radius_account(self):
        user = SimpleNamespace(email='user@example.com', expiration=None)
        expiration = datetime.date(2026, 12, 31)

        with patch.object(self.VPNAccount, 'get_account_by_email', return_value=Mock()), \
                patch.object(self.VPNAccount, 'delete') as delete:
            self.User.set_expiration(user, expiration, delete=True)

        self.assertEqual(user.expiration, expiration)
        delete.assert_called_once_with('user@example.com')


class RepositoryContractTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_docker_context_excludes_operator_files(self):
        dockerignore = (self.root / '.dockerignore').read_text(encoding='utf-8').splitlines()
        self.assertIn('/app/doc', dockerignore)
        self.assertIn('/config/default.py', dockerignore)

    def test_document_submodule_is_removed(self):
        self.assertFalse((self.root / '.gitmodules').exists())

    def test_missing_operator_config_uses_example_defaults(self):
        init_source = (self.root / 'app' / '__init__.py').read_text(encoding='utf-8')
        self.assertIn("app.config.from_object('config.example')", init_source)
        self.assertIn("import_module('config.default')", init_source)

    def test_bootstrap_4_assets_and_dependencies(self):
        bootstrap_css = (
            self.root / 'app' / 'static' / 'css' / 'bootstrap.min.css'
        ).read_text(encoding='utf-8')
        bootstrap_js = (
            self.root / 'app' / 'static' / 'js' / 'bootstrap.bundle.min.js'
        ).read_text(encoding='utf-8')
        requirements = (self.root / 'requirements.txt').read_text(encoding='utf-8')

        self.assertIn('Bootstrap v4.6.2', bootstrap_css[:300])
        self.assertIn('Bootstrap v4.6.2', bootstrap_js[:300])
        self.assertNotIn('Flask-Bootstrap', requirements)

    def test_templates_do_not_use_bootstrap_3_components(self):
        forbidden = (
            'btn-default', 'panel-default', 'panel-heading', 'panel-body',
            'panel-title', 'label-info', 'label-success', 'label-danger',
            'class="well', 'list-group-item-heading',
            'list-group-item-text', ' active in',
        )
        for template in (self.root / 'app' / 'templates').rglob('*.html'):
            source = template.read_text(encoding='utf-8')
            for token in forbidden:
                with self.subTest(template=template.name, token=token):
                    self.assertNotIn(token, source)


if __name__ == '__main__':
    unittest.main()
