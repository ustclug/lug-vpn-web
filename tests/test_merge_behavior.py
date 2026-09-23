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
format_calling_station_id = utils.format_calling_station_id


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


class CallingStationIdTests(unittest.TestCase):
    def test_decodes_quoted_printable_ipv6_port_brackets(self):
        self.assertEqual(
            format_calling_station_id('2001:db8::1=5B4500=5D'),
            '2001:db8::1[4500]',
        )

    def test_preserves_unencoded_addresses(self):
        self.assertEqual(format_calling_station_id('192.0.2.1'), '192.0.2.1')
        self.assertEqual(format_calling_station_id('2001:db8::1'), '2001:db8::1')

    def test_none_is_rendered_as_empty(self):
        self.assertEqual(format_calling_station_id(None), '')


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
    @patch.object(utils.time, 'sleep')
    def test_network_errors_are_retried_up_to_three_times(self, sleep, get):
        with self.assertRaises(LibraryAPIError):
            fetch_from_lib_api('https://library.example/check', 'PB123')

        self.assertEqual(get.call_count, 4)
        self.assertEqual(sleep.call_args_list, [unittest.mock.call(1)] * 3)

    @patch.object(utils.requests, 'get')
    @patch.object(utils.time, 'sleep')
    def test_network_error_is_retried_until_success(self, sleep, get):
        response = Mock()
        response.content = b'<reader_info><name>Alice</name><type>Student</type></reader_info>'
        response.raise_for_status.return_value = None
        get.side_effect = [requests.Timeout(), response]

        result = fetch_from_lib_api('https://library.example/check', 'PB123')

        self.assertEqual(result, {'name': 'Alice', 'type': 'Student'})
        self.assertEqual(get.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch.object(utils.requests, 'get')
    @patch.object(utils.time, 'sleep')
    def test_http_status_is_preserved_after_retries(self, sleep, get):
        response = Mock(status_code=503)
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
        get.return_value = response

        with self.assertRaises(LibraryAPIError) as raised:
            fetch_from_lib_api('https://library.example/check', 'PB123')

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(get.call_count, 4)
        self.assertEqual(sleep.call_args_list, [unittest.mock.call(1)] * 3)

    @patch.object(utils.requests, 'get')
    def test_not_found_response_is_returned_for_caller_handling(self, get):
        response = Mock()
        response.content = (
            b'<reader_info><ip>202.38.95.102</ip>'
            b'<status>not found</status><count>0</count></reader_info>'
        )
        response.raise_for_status.return_value = None
        get.return_value = response

        result = fetch_from_lib_api('https://library.example/check', 'PB123')

        self.assertEqual(result['status'], 'not found')

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


class RejectApplicationViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from app import app
            from app import views
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest('application dependencies are unavailable') from exc
        cls.app = app
        cls.views = views

    def test_application_details_are_rendered_before_reject_reason(self):
        user = SimpleNamespace(
            email='applicant@example.com',
            name='Test Applicant',
            studentno='PB12345678',
            phone='123456789',
            reason='Student qualification',
            applytime=datetime.datetime(2026, 9, 9, 12, 30),
            renewing=False,
            rejectreason=None,
            expiration=None,
        )

        with patch.dict(self.app.config, {'WTF_CSRF_ENABLED': False}), \
                self.app.test_request_context('/reject/42'), patch.object(
                    self.views, 'current_user', SimpleNamespace(admin=True)
                ), patch.object(
                    self.views.User, 'get_user_by_id', return_value=user
                ):
            response = self.views.reject.__wrapped__(42)

        self.assertIn('Test Applicant', response)
        self.assertIn('PB12345678', response)
        self.assertIn('123456789', response)
        self.assertIn('Student qualification', response)
        self.assertIn('2026-09-09 12:30:00', response)
        self.assertLess(
            response.index('Application details'),
            response.index('Reject reason'),
        )


class ManageUsersLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from app import app
            from app import views
            from app.models import User
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest('application dependencies are unavailable') from exc
        cls.app = app
        cls.views = views
        cls.User = User

    def test_data_returns_all_users_regardless_of_url_filters(self):
        users = [SimpleNamespace(email=f'user{i}@example.com') for i in range(60)]
        rejected = [SimpleNamespace(email=f'rejected{i}@example.com') for i in range(30)]
        with self.app.test_request_context('/manageusers/data/?q=missing&offset=25&sort=email'), patch.object(
            self.views, 'current_user', SimpleNamespace(admin=True, is_authenticated=True)
        ), patch.object(self.User, 'get_users_with_traffic', return_value=[(u, 1024, 2048) for u in users]) as active, patch.object(
            self.User, 'get_rejected', return_value=rejected
        ) as rejected_query, patch.object(self.views, 'render_template', return_value='fragment') as render:
            response = self.views.manage_users_data()
        active.assert_called_once_with()
        rejected_query.assert_called_once_with()
        self.assertEqual(render.call_args.kwargs['users'], users)
        self.assertEqual(render.call_args.kwargs['rejected_users'], rejected)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(response.get_json(), {'html': 'fragment'})

    def test_all_active_users_are_loaded_with_traffic_and_zero_defaults(self):
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session
        from app import db
        engine = create_engine('sqlite://')
        self.User.__table__.create(engine)
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE monthtraffic (UserName TEXT, TrafficSum INTEGER)'))
            connection.execute(text('CREATE TABLE lastmonthtraffic (UserName TEXT, TrafficSum INTEGER)'))
            connection.execute(self.User.__table__.insert(), [
                dict(id=i, email=f'user{i}@example.com', passwordhash='test', salt='test',
                     status='pass' if i < 60 else ('banned' if i == 60 else 'reject'))
                for i in range(1, 62)
            ])
            connection.execute(text("INSERT INTO monthtraffic VALUES ('user60@example.com', 2048)"))
        with Session(engine) as session, patch.object(db, 'session', session):
            rows = self.User.get_users_with_traffic()
            self.assertEqual(len(rows), 60)
            self.assertEqual(tuple(rows[0])[1:], (0, 0))
            self.assertEqual(rows[-1][0].id, 60)
            self.assertEqual(tuple(rows[-1])[1:], (0, 2048))
        engine.dispose()

    def test_initial_page_does_not_query_lists(self):
        with self.app.test_request_context('/manageusers/?q=Alice'), patch.object(
            self.views, 'current_user', SimpleNamespace(admin=True)
        ), patch.object(self.User, 'get_users_with_traffic') as active, patch.object(
            self.User, 'get_rejected'
        ) as rejected:
            html = self.views.manage_users.__wrapped__()
        active.assert_not_called()
        rejected.assert_not_called()
        self.assertIn('manageusers.js', html)
        self.assertIn('value="Alice"', html)

    def test_data_requires_authenticated_admin_before_queries(self):
        for user, status in [
            (SimpleNamespace(is_authenticated=False), 401),
            (SimpleNamespace(is_authenticated=True, admin=False), 403),
        ]:
            with self.subTest(status=status), self.app.test_request_context(
                '/manageusers/data/'
            ), patch.object(self.views, 'current_user', user), patch.object(
                self.User, 'get_users_with_traffic'
            ) as active, patch.object(self.User, 'get_rejected') as rejected:
                response, code = self.views.manage_users_data()
            self.assertEqual(code, status)
            active.assert_not_called()
            rejected.assert_not_called()

    def test_fragment_escapes_user_data_and_preserves_post_actions(self):
        user = SimpleNamespace(
            id=1, email='alice@example.com', name='<script>alert(1)</script>',
            studentno='PB100', expiration=None, admin=False, status='pass',
        )
        rejected_user = SimpleNamespace(
            id=2, email='bob@example.com', name='Bob', studentno='PB200',
            rejectreason='<img src=x onerror=alert(1)>', applytime=None,
        )
        with self.app.test_request_context('/manageusers/data/'), patch.object(
            self.views, 'current_user', SimpleNamespace(admin=True, is_authenticated=True)
        ), patch.object(self.User, 'get_users_with_traffic', return_value=[(user, 1024, 2048)]), patch.object(
            self.User, 'get_rejected', return_value=[rejected_user]
        ):
            html = self.views.manage_users_data().get_json()['html']
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;img', html)
        self.assertIn('method="post"', html)
        for label in ['Set admin', 'Renew Semester', 'Pass Semester', 'Edit reason']:
            self.assertIn(label, html)
        self.assertNotIn('<html', html)


class ApplicationQualificationValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from app import app
            from app import views
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest('application dependencies are unavailable') from exc
        cls.app = app
        cls.views = views

    def test_first_configured_qualification_is_the_default(self):
        user = SimpleNamespace(status='none')
        config = {
            'APPLICATION_REASONS': ['Student', 'Staff'],
            'APPLICATION_CONFIRMATION_ENABLED': False,
            'CONSTITUTION_DOCUMENTS': [],
            'TERMS_DOCUMENTS': [],
            'WTF_CSRF_ENABLED': False,
        }

        with patch.dict(self.app.config, config), self.app.test_request_context(
            '/apply/'
        ), patch.object(
            self.views, 'current_user', user
        ), patch.object(
            self.views, 'render_document_set', return_value=[]
        ):
            response = self.views.apply.__wrapped__()

        self.assertNotIn('Select a qualification', response)
        self.assertLess(
            response.index('<option value="Student">Student</option>'),
            response.index('<option value="Staff">Staff</option>'),
        )

    def test_empty_qualification_is_allowed(self):
        user = SimpleNamespace(
            status='none', email='test@example.com', save=Mock(),
        )
        form_data = {
            'name': 'Test User',
            'studentno': 'PB12345678',
            'phone': '123456789',
            'reasonClass': '',
            'reasonText': '',
            'agree': 'y',
        }
        config = {
            'APPLICATION_REASONS': ['Student'],
            'APPLICATION_CONFIRMATION_ENABLED': False,
            'CONSTITUTION_DOCUMENTS': [],
            'TERMS_DOCUMENTS': [],
            'WTF_CSRF_ENABLED': False,
        }

        with patch.dict(self.app.config, config), self.app.test_request_context(
            '/apply/', method='POST', data=form_data
        ), patch.object(
            self.views, 'current_user', user
        ), patch.object(
            self.views, 'render_document_set', return_value=[]
        ), patch.object(
            self.views, 'send_mail'
        ):
            response = self.views.apply.__wrapped__()

        self.assertEqual(response.status_code, 302)
        user.save.assert_called_once_with()
        self.assertEqual(user.status, 'applying')
        self.assertEqual(user.reason, '')

    def test_library_api_details_are_added_to_application_email(self):
        user = SimpleNamespace(
            status='none', email='test@example.com', save=Mock(),
        )
        form_data = {
            'name': 'Test User',
            'studentno': 'PB12345678',
            'phone': '123456789',
            'reasonClass': 'Student',
            'reasonText': 'Member of robotics club',
            'agree': 'y',
        }
        config = {
            'APPLICATION_REASONS': ['Student'],
            'APPLICATION_CONFIRMATION_ENABLED': False,
            'CONSTITUTION_DOCUMENTS': [],
            'TERMS_DOCUMENTS': [],
            'WTF_CSRF_ENABLED': False,
            'LIBRARY_API_URL': 'https://library.example/check',
            'LIBRARY_API_TIMEOUT': 5,
        }

        with patch.dict(self.app.config, config), self.app.test_request_context(
            '/apply/', method='POST', data=form_data
        ), patch.object(
            self.views, 'current_user', user
        ), patch.object(
            self.views, 'fetch_from_lib_api',
            return_value={'name': '张三', 'type': '学生'},
        ) as fetch, patch.object(
            self.views, 'send_mail'
        ) as send_mail:
            response = self.views.apply.__wrapped__()

        self.assertEqual(response.status_code, 302)
        fetch.assert_called_once_with(
            'https://library.example/check', 'PB12345678', timeout=5,
        )
        email_html = send_mail.call_args.args[1]
        self.assertIn(
            '<br>Qualification: Student'
            '<br>Additional info: Member of robotics club'
            '<hr>Library API Name: 张三'
            '<br>Library API Type: 学生',
            email_html,
        )
        self.assertNotIn('<br>Reason:', email_html)

    def test_library_api_not_found_is_added_to_application_email(self):
        self._assert_library_api_email_result(
            {'status': 'not found', 'count': '0'},
            '<hr>Library API: user not found',
        )

    def test_library_api_http_failure_is_added_to_application_email(self):
        self._assert_library_api_email_result(
            self.views.LibraryAPIError('Library API request failed', status_code=503),
            '<hr>Failed to query Library API (HTTP status 503)',
            raises=True,
        )

    def _assert_library_api_email_result(self, result, expected, raises=False):
        user = SimpleNamespace(
            status='none', email='test@example.com', save=Mock(),
        )
        form_data = {
            'name': 'Test User',
            'studentno': 'PB12345678',
            'phone': '123456789',
            'reasonClass': 'Student',
            'reasonText': '',
            'agree': 'y',
        }
        config = {
            'APPLICATION_REASONS': ['Student'],
            'APPLICATION_CONFIRMATION_ENABLED': False,
            'CONSTITUTION_DOCUMENTS': [],
            'TERMS_DOCUMENTS': [],
            'WTF_CSRF_ENABLED': False,
            'LIBRARY_API_URL': 'https://library.example/check',
            'LIBRARY_API_TIMEOUT': 5,
        }
        fetch_result = {'side_effect' if raises else 'return_value': result}

        with patch.dict(self.app.config, config), self.app.test_request_context(
            '/apply/', method='POST', data=form_data
        ), patch.object(
            self.views, 'current_user', user
        ), patch.object(
            self.views, 'fetch_from_lib_api', **fetch_result
        ), patch.object(
            self.views, 'send_mail'
        ) as send_mail:
            response = self.views.apply.__wrapped__()

        self.assertEqual(response.status_code, 302)
        email_html = send_mail.call_args.args[1]
        self.assertIn(expected, email_html)
        self.assertNotIn('Library API Name:', email_html)
        self.assertNotIn('Library API Type:', email_html)
        self.assertNotIn('Unavailable', email_html)


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

    def test_bootstrap_5_assets_and_dependencies(self):
        bootstrap_css = (
            self.root / 'app' / 'static' / 'css' / 'bootstrap.min.css'
        ).read_text(encoding='utf-8')
        bootstrap_js = (
            self.root / 'app' / 'static' / 'js' / 'bootstrap.bundle.min.js'
        ).read_text(encoding='utf-8')
        requirements = (self.root / 'requirements.txt').read_text(encoding='utf-8')

        self.assertIn('v5.3.8', bootstrap_css[:300])
        self.assertIn('v5.3.8', bootstrap_js[:300])
        self.assertNotIn('Flask-Bootstrap', requirements)

    def test_templates_do_not_use_bootstrap_4_markup(self):
        forbidden = (
            'data-toggle=', 'data-target=', 'data-dismiss=',
            'class="close"', 'badge-info', 'badge-success', 'badge-danger',
            'custom-control', 'custom-checkbox', 'custom-control-input',
            'custom-control-label', 'form-group',
        )
        for template in (self.root / 'app' / 'templates').rglob('*.html'):
            source = template.read_text(encoding='utf-8')
            for token in forbidden:
                with self.subTest(template=template.name, token=token):
                    self.assertNotIn(token, source)

    def test_datatables_is_not_vendored_or_referenced(self):
        for path in (self.root / 'app').rglob('*'):
            if not path.is_file():
                continue
            with self.subTest(path=path.relative_to(self.root)):
                self.assertNotIn('datatable', path.name.lower())
                if path.suffix in {'.html', '.js', '.py'}:
                    source = path.read_text(encoding='utf-8')
                    self.assertNotIn('DataTable', source)

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

    def test_application_form_has_no_frontend_non_empty_qualification_check(self):
        source = (
            self.root / 'app' / 'templates' / 'apply.html'
        ).read_text(encoding='utf-8')

        self.assertNotIn('qualificationNotice', source)
        self.assertNotIn('qualificationIsChosen', source)
        self.assertIn("$('#applyForm').on('submit'", source)


if __name__ == '__main__':
    unittest.main()
