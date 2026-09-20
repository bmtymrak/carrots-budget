from django.test import RequestFactory, SimpleTestCase

from project.http import safe_next_url


class SafeNextUrlTests(SimpleTestCase):
    def test_destinations(self):
        cases = [
            ('/purchases?search=food&page=2', '/purchases?search=food&page=2'),
            (' http://testserver:8000/budgets?ytd=4 ', 'http://testserver:8000/budgets?ytd=4'),
            ('https://testserver:8000/budgets', 'https://testserver:8000/budgets'),
            ('//testserver:8000/budgets', '//testserver:8000/budgets'),
            ('', '/fallback'), ('   ', '/fallback'),
            ('//evil.test/path', '/fallback'),
            ('https://evil.test/path', '/fallback'),
            ('http://testserver/budgets', '/fallback'),
            ('/\\evil.test', '/fallback'), ('\\\\evil.test', '/fallback'),
            ('javascript:alert(1)', '/fallback'), ('ftp://testserver:8000/a', '/fallback'),
            ('http:///evil.test', '/fallback'), ('https://[broken', '/fallback'),
            ('/safe\r\nInjected: bad', '/fallback'), ('/safe\tpath', '/fallback'),
            ('/safe\x00path', '/fallback'), ('/safe\x7fpath', '/fallback'),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                request = RequestFactory().get('/', {'next': value}, HTTP_HOST='testserver:8000')
                self.assertEqual(safe_next_url(request, fallback='/fallback'), expected)

    def test_post_key_precedence_and_delete_query(self):
        for data, expected in [({}, '/query?a=1'), ({'next': '/post'}, '/post'),
                               ({'next': ''}, '/fallback'),
                               ({'next': 'https://evil.test'}, '/fallback')]:
            with self.subTest(data=data):
                request = RequestFactory().post('/?next=/query%3Fa%3D1', data)
                self.assertEqual(safe_next_url(request, fallback='/fallback'), expected)
        request = RequestFactory().delete('/?next=/query%3Fa%3D1')
        self.assertEqual(safe_next_url(request, fallback='/fallback'), '/query?a=1')

    def test_exact_paths_and_https(self):
        for value, expected in [('/month?filter=1', '/month?filter=1'),
                                ('/month/other', '/fallback'), ('/year', '/fallback'),
                                ('https://testserver/month?q=2', 'https://testserver/month?q=2')]:
            request = RequestFactory().get('/', {'next': value})
            self.assertEqual(safe_next_url(request, fallback='/fallback', allowed_paths={'/month'}), expected)
        request = RequestFactory().get('/', {'next': 'http://testserver/month'}, secure=True)
        self.assertEqual(safe_next_url(request, fallback='/fallback'), '/fallback')

    def test_fallback_must_be_nonempty_and_trusted(self):
        request = RequestFactory().get('/')
        for fallback in ['', ' ', 'https://evil.test', '/bad\nheader']:
            with self.subTest(fallback=fallback), self.assertRaises(ValueError):
                safe_next_url(request, fallback=fallback)
